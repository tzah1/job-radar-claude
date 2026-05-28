#!/usr/bin/env python3
"""
find_career_urls.py - Populate missing career_url values in target_companies.csv

Strategy:
  1. Check KNOWN_CAREER_URLS dict (high-confidence, manually curated)
  2. For unknown companies, try common URL patterns with HTTP HEAD verification
  3. Only write a URL if confidence is "high" (verified or known)
  4. Mark everything else as needing manual review — never hallucinate URLs

After running, edit config/target_companies.csv manually to fill remaining blanks.

Usage:
    python scripts/find_career_urls.py [--dry-run] [--verify]
    --verify : also run HTTP HEAD check on URLs already in the CSV
"""

import csv
import sys
import time
import logging
import argparse
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
COMPANIES_CSV = BASE_DIR / "config" / "target_companies.csv"
LOG_FILE = BASE_DIR / "logs" / "daily_scan.log"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ── High-confidence known URLs ────────────────────────────────────────────────
# Only add here when you are certain of the URL.
# Verify manually at https://company.com/careers before adding.
KNOWN_CAREER_URLS = {
    "Forter":               "https://www.forter.com/careers/",
    "Lemonade":             "https://makers.lemonade.com/",
    "Fireblocks":           "https://www.fireblocks.com/company/careers/",
    "Palo Alto Networks":   "https://www.paloaltonetworks.com/company/careers",
    "Tenable":              "https://www.tenable.com/careers",
    "Wiz":                  "https://www.wiz.io/careers",
    "Melio":                "https://www.meliopayments.com/careers",
    "Imperva":              "https://www.imperva.com/careers/",
    "Mixtiles":             "https://www.mixtiles.com/careers",
    "ControlUp":            "https://www.controlup.com/about-us/careers/",
    "Zenity":               "https://www.zenity.io/careers/",
    # TODO: find and verify URLs for:
    #   Eleos Health, Cyara, Dream Security, Dfingo, Oasis,
    #   Zenzap, Neo Security, Ocean, Harmony
}

REQUEST_TIMEOUT = 10
REQUEST_DELAY = 1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobRadar/1.0)",
}


def verify_url(url: str) -> bool:
    """Return True if URL returns a successful response (< 400)."""
    try:
        resp = requests.head(
            url, timeout=REQUEST_TIMEOUT, allow_redirects=True, headers=HEADERS
        )
        if resp.status_code == 405:
            # HEAD not allowed — try GET
            resp = requests.get(
                url, timeout=REQUEST_TIMEOUT, allow_redirects=True,
                headers=HEADERS, stream=True
            )
            resp.close()
        return resp.status_code < 400
    except Exception as e:
        log.debug(f"Verify failed for {url}: {e}")
        return False


def process(dry_run: bool = False, verify: bool = False):
    rows = []
    with open(COMPANIES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated = 0
    manual_needed = []

    for row in rows:
        name = row["company_name"].strip()
        existing_url = row.get("career_url", "").strip()

        # Optionally verify existing URLs
        if existing_url and verify:
            ok = verify_url(existing_url)
            status = "OK" if ok else "BROKEN"
            log.info(f"[VERIFY] {name}: {existing_url} → {status}")
            time.sleep(REQUEST_DELAY)
            continue

        if existing_url:
            log.info(f"[SKIP]   {name} — URL already set")
            continue

        if name in KNOWN_CAREER_URLS:
            url = KNOWN_CAREER_URLS[name]
            log.info(f"[FOUND]  {name} → {url}")
            if not dry_run:
                row["career_url"] = url
                updated += 1
            time.sleep(REQUEST_DELAY)
        else:
            log.info(f"[MANUAL] {name} — no known URL, needs manual entry")
            manual_needed.append(name)

    if not dry_run and updated > 0:
        with open(COMPANIES_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        log.info(f"Wrote {updated} career URLs to {COMPANIES_CSV.relative_to(BASE_DIR)}")

    print("\n" + "=" * 50)
    if updated:
        print(f"Updated {updated} career URLs (confirm in config/target_companies.csv)")
    if manual_needed:
        print(f"\nNeeds manual career URL entry ({len(manual_needed)} companies):")
        for c in manual_needed:
            print(f"  • {c}")
        print("\nEdit config/target_companies.csv and fill in the career_url column.")
    if dry_run:
        print("\n[DRY RUN] No changes written.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find and populate career URLs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--verify", action="store_true", help="Verify existing URLs with HTTP check")
    args = parser.parse_args()
    process(dry_run=args.dry_run, verify=args.verify)
