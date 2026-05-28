#!/usr/bin/env python3
"""
parse_jobs.py - Parse fetched HTML and manual JSON into structured job records

Sources (in priority order):
  1. data/raw/manual/*.json  — manually entered job descriptions (always processed)
  2. data/raw/<company>/*.html — fetched HTML (company-specific parsers, v1 is stub)

Output: data/parsed/YYYYMMDD_parsed_jobs.json

Manual job JSON format (one file per batch):
[
  {
    "company_name": "Acme",
    "role_title": "Data Engineer",
    "location": "Tel Aviv",
    "work_model": "hybrid",
    "job_url": "https://...",
    "description": "Full job description text...",
    "notes": "optional notes"
  }
]
Single job dict (not wrapped in list) is also accepted.

Usage:
    python scripts/parse_jobs.py [--dry-run]
    Also importable: run(dry_run) -> list[dict]
"""

import csv
import json
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
MANUAL_DIR = RAW_DIR / "manual"
PARSED_DIR = DATA_DIR / "parsed"
LOG_FILE = BASE_DIR / "logs" / "daily_scan.log"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

REQUIRED_FIELDS = ["company_name", "role_title"]
JOB_FIELDS = [
    "job_id", "date_found", "company_name", "role_title", "role_category",
    "detected_sector", "location", "work_model", "job_url", "description",
    "fit_score", "fit_summary", "risks", "approved_for_cv", "status", "notes",
]


def make_job_id(company: str, title: str, url: str) -> str:
    raw = f"{company.lower().strip()}|{title.lower().strip()}|{url.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def normalize(raw: dict) -> dict | None:
    """Normalize a raw job dict to the standard schema. Returns None if invalid."""
    for f in REQUIRED_FIELDS:
        if not str(raw.get(f, "")).strip():
            log.warning(f"Skipping record missing '{f}': {raw}")
            return None

    company = str(raw.get("company_name", "")).strip()
    title = str(raw.get("role_title", "")).strip()
    url = str(raw.get("job_url", "")).strip()

    return {
        "job_id": make_job_id(company, title, url),
        "date_found": raw.get("date_found") or datetime.now().strftime("%Y-%m-%d"),
        "company_name": company,
        "role_title": title,
        "role_category": str(raw.get("role_category", "")).strip(),
        "detected_sector": str(raw.get("detected_sector", "")).strip(),
        "location": str(raw.get("location", "")).strip(),
        "work_model": str(raw.get("work_model", "")).strip(),
        "job_url": url,
        "description": str(raw.get("description", "")).strip(),
        "fit_score": "",
        "fit_summary": "",
        "risks": "",
        "approved_for_cv": "",
        "status": "new",
        "notes": str(raw.get("notes", "")).strip(),
    }


def parse_manual_jobs() -> list:
    """Load and normalize all JSON files from data/raw/manual/."""
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    for fpath in sorted(MANUAL_DIR.glob("*.json")):
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"Could not read {fpath.name}: {e}")
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            job = normalize(item)
            if job:
                jobs.append(job)
                log.info(f"  manual: {job['company_name']} — {job['role_title']}")
            else:
                log.warning(f"  skipped invalid record in {fpath.name}")
    return jobs


def parse_html_for_company(company_name: str, html_file: Path) -> list:
    """
    Parse a raw HTML file for a company's career page.
    v1: stub — HTML parsing is site-specific and must be implemented per company.
    See docs/source_characterization.md for the roadmap.

    TODO: implement company-specific selectors here as companies are characterized.
    Example structure when implemented:
        soup = BeautifulSoup(html_file.read_text(), "html.parser")
        # Use soup.select("...") with the company's job card selector
    """
    if not BS4_AVAILABLE:
        log.debug(f"beautifulsoup4 not installed — skipping HTML parse for {company_name}")
        return []
    # TODO: add company-specific HTML parsing logic
    log.debug(f"HTML parser not yet implemented for {company_name} — {html_file.name}")
    return []


def parse_all_raw_html() -> list:
    """Walk data/raw/<company>/ dirs and attempt to parse HTML files."""
    jobs = []
    if not RAW_DIR.exists():
        return jobs
    for company_dir in sorted(RAW_DIR.iterdir()):
        if not company_dir.is_dir() or company_dir.name == "manual":
            continue
        company_name = company_dir.name.replace("_", " ").title()
        for html_file in sorted(company_dir.glob("*.html")):
            parsed = parse_html_for_company(company_name, html_file)
            jobs.extend(parsed)
    return jobs


def save_parsed(jobs: list) -> Path:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    out = PARSED_DIR / f"{date_str}_parsed_jobs.json"
    out.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Saved {len(jobs)} parsed jobs → {out.relative_to(BASE_DIR)}")
    return out


def run(dry_run: bool = False) -> list:
    all_jobs = []
    all_jobs.extend(parse_manual_jobs())
    all_jobs.extend(parse_all_raw_html())

    # Deduplicate by job_id (keep first occurrence)
    seen_ids = set()
    unique = []
    for job in all_jobs:
        if job["job_id"] not in seen_ids:
            seen_ids.add(job["job_id"])
            unique.append(job)

    log.info(f"Parsed {len(all_jobs)} total jobs, {len(unique)} unique")

    if not dry_run:
        save_parsed(unique)

    return unique


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse fetched job data into structured records")
    parser.add_argument("--dry-run", action="store_true", help="Parse without saving")
    args = parser.parse_args()
    jobs = run(dry_run=args.dry_run)
    log.info(f"Done. {len(jobs)} jobs.")
