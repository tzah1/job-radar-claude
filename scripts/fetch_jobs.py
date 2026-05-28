#!/usr/bin/env python3
"""
fetch_jobs.py - Fetch raw HTML from company career pages

v1 behavior:
  - Tries a polite GET request to career_url
  - Saves raw HTML to data/raw/<company_slug>/YYYYMMDD_careers.html
  - Returns list of dicts indicating fetch status per company
  - Does NOT parse jobs — that is done by parse_jobs.py

Companies with no career_url are marked status=manual_check_required.
Manual data under data/raw/manual/ is used by parse_jobs.py directly (not here).

A REQUEST_DELAY is enforced between requests to be polite.

Usage:
    python scripts/fetch_jobs.py [--dry-run] [--company "Company Name"]
    Also importable: run(company_filter, dry_run) -> list[dict]
"""

import csv
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
COMPANIES_CSV = CONFIG_DIR / "target_companies.csv"
LOG_FILE = BASE_DIR / "logs" / "daily_scan.log"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

REQUEST_DELAY = 3      # seconds between company requests
REQUEST_TIMEOUT = 15   # seconds per request

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def company_slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("/", "_")


def fetch_url(url: str) -> tuple:
    """Fetch a URL. Returns (html_text | None, status_code)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        return resp.text, resp.status_code
    except requests.exceptions.Timeout:
        log.warning(f"Timeout fetching {url}")
        return None, 0
    except requests.exceptions.ConnectionError:
        log.warning(f"Connection error fetching {url}")
        return None, 0
    except Exception as e:
        log.warning(f"Unexpected error fetching {url}: {e}")
        return None, 0


def save_raw_html(company_name: str, content: str) -> Path:
    slug = company_slug(company_name)
    out_dir = RAW_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    out_file = out_dir / f"{date_str}_careers.html"
    out_file.write_text(content, encoding="utf-8", errors="replace")
    log.info(f"  saved raw HTML → {out_file.relative_to(BASE_DIR)}")
    return out_file


def load_companies(company_filter: str | None = None) -> list:
    companies = []
    with open(COMPANIES_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["company_name"].strip()
            if company_filter and name.lower() != company_filter.lower():
                continue
            companies.append(row)
    return companies


def run(company_filter: str | None = None, dry_run: bool = False) -> list:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    companies = load_companies(company_filter)
    results = []

    for i, company in enumerate(companies):
        name = company["company_name"].strip()
        url = company.get("career_url", "").strip()

        if not url:
            log.info(f"[{name}] No career_url — manual_check_required")
            results.append({"company_name": name, "status": "manual_check_required",
                            "career_url": "", "http_status": None})
            continue

        log.info(f"[{name}] Fetching {url}")

        if dry_run:
            log.info(f"[{name}] [DRY RUN] skipping HTTP request")
            results.append({"company_name": name, "status": "dry_run",
                            "career_url": url, "http_status": None})
            continue

        html, status = fetch_url(url)

        if html and status < 400:
            save_raw_html(name, html)
            results.append({"company_name": name, "status": "fetched",
                            "career_url": url, "http_status": status})
        else:
            log.warning(f"[{name}] Fetch failed — status={status}")
            results.append({"company_name": name, "status": "fetch_failed",
                            "career_url": url, "http_status": status})

        # Polite delay — not on the last item
        if i < len(companies) - 1 and not dry_run:
            time.sleep(REQUEST_DELAY)

    fetched = sum(1 for r in results if r["status"] == "fetched")
    manual = sum(1 for r in results if r["status"] == "manual_check_required")
    failed = sum(1 for r in results if r["status"] == "fetch_failed")
    log.info(f"Fetch complete — {fetched} fetched, {manual} manual check, {failed} failed")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch career pages for target companies")
    parser.add_argument("--company", help="Filter to a single company name")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual HTTP requests")
    args = parser.parse_args()
    run(company_filter=args.company, dry_run=args.dry_run)
