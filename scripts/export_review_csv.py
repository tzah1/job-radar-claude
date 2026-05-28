#!/usr/bin/env python3
"""
export_review_csv.py - Export scored jobs to review CSV and Markdown

Inputs:
  - Scored job list (passed from run_daily_scan.py, or reads latest parsed JSON)
  - data/seen_jobs.csv      — for deduplication
  - data/rejected_jobs.csv  — for filtering out already-rejected jobs

Outputs:
  - exports/jobs_for_review.csv  — appends new jobs (preserves existing approved/reviewed rows)
  - exports/jobs_for_review.md   — full regeneration sorted by fit_score desc
  - Updates data/seen_jobs.csv   — marks new jobs as "new"

Design: jobs_for_review.csv is the single source of truth for your review.
  Existing rows with approved_for_cv filled in are never overwritten.
  New jobs are appended with status=new.

Usage:
    python scripts/export_review_csv.py [--dry-run]
    Also importable: run(scored_jobs, dry_run) -> int  (returns count of new jobs added)
"""

import csv
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
PARSED_DIR = DATA_DIR / "parsed"

SEEN_CSV = DATA_DIR / "seen_jobs.csv"
REJECTED_CSV = DATA_DIR / "rejected_jobs.csv"
REVIEW_CSV = EXPORTS_DIR / "jobs_for_review.csv"
REVIEW_MD = EXPORTS_DIR / "jobs_for_review.md"

LOG_FILE = BASE_DIR / "logs" / "daily_scan.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

REVIEW_FIELDS = [
    "job_id", "date_found", "company_name", "role_title", "role_category",
    "detected_sector", "location", "work_model", "job_url", "fit_score",
    "fit_summary", "risks", "approved_for_cv", "status", "notes",
]

SEEN_FIELDS = ["job_id", "company_name", "role_title", "job_url",
               "first_seen", "last_seen", "status"]


def _load_csv_ids(path: Path, id_col: str = "job_id") -> set:
    if not path.exists():
        return set()
    with open(path, newline="", encoding="utf-8") as f:
        return {row[id_col] for row in csv.DictReader(f) if row.get(id_col)}


def _load_review_csv() -> list:
    if not REVIEW_CSV.exists():
        return []
    with open(REVIEW_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save_review_csv(rows: list):
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _update_seen_csv(new_jobs: list):
    existing = {}
    if SEEN_CSV.exists():
        with open(SEEN_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["job_id"]] = row

    today = datetime.now().strftime("%Y-%m-%d")
    for job in new_jobs:
        jid = job["job_id"]
        if jid in existing:
            existing[jid]["last_seen"] = today
            existing[jid]["status"] = job.get("status", "new")
        else:
            existing[jid] = {
                "job_id": jid,
                "company_name": job.get("company_name", ""),
                "role_title": job.get("role_title", ""),
                "job_url": job.get("job_url", ""),
                "first_seen": today,
                "last_seen": today,
                "status": job.get("status", "new"),
            }

    with open(SEEN_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SEEN_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing.values())


def _write_review_md(all_rows: list):
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    # Sort: new first, then by fit_score descending
    def sort_key(r):
        score = int(r.get("fit_score") or 0)
        is_new = 1 if r.get("status") == "new" else 0
        return (-is_new, -score)

    sorted_rows = sorted(all_rows, key=sort_key)

    lines = [
        f"# Jobs For Review — {today}",
        "",
        f"**Total jobs**: {len(all_rows)}  |  "
        f"**New**: {sum(1 for r in all_rows if r.get('status') == 'new')}  |  "
        f"**Pending review**: {sum(1 for r in all_rows if not r.get('approved_for_cv'))}",
        "",
        "---",
        "",
    ]

    for r in sorted_rows:
        score = r.get("fit_score", "?")
        approved = r.get("approved_for_cv", "")
        status_tag = f"[{r.get('status', '').upper()}]" if r.get("status") else ""
        approved_tag = f"✅ approved" if approved == "yes" else ("❌ no" if approved == "no" else "⏳ pending")

        lines.append(f"## {r.get('company_name', '')} — {r.get('role_title', '')}  {status_tag}")
        lines.append("")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| job_id | `{r.get('job_id', '')}` |")
        lines.append(f"| Date found | {r.get('date_found', '')} |")
        lines.append(f"| Category | {r.get('role_category', '')} |")
        lines.append(f"| Sector | {r.get('detected_sector', '')} |")
        lines.append(f"| Location | {r.get('location', '')} |")
        lines.append(f"| Work model | {r.get('work_model', '')} |")
        lines.append(f"| Fit score | **{score}/10** |")
        lines.append(f"| Approved for CV | {approved_tag} |")
        if r.get("job_url"):
            lines.append(f"| URL | [{r['job_url'][:60]}...]({r['job_url']}) |")
        lines.append("")
        if r.get("fit_summary"):
            lines.append(f"**Fit**: {r['fit_summary']}")
            lines.append("")
        if r.get("risks"):
            lines.append(f"**Risks**: {r['risks']}")
            lines.append("")
        if r.get("notes"):
            lines.append(f"**Notes**: {r['notes']}")
            lines.append("")
        lines.append("---")
        lines.append("")

    REVIEW_MD.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Written → {REVIEW_MD.relative_to(BASE_DIR)}")


def run(scored_jobs: list | None = None, dry_run: bool = False) -> int:
    # Load inputs
    if scored_jobs is None:
        # Fall back to latest parsed+scored JSON in data/parsed/
        parsed_files = sorted(PARSED_DIR.glob("*_parsed_jobs.json"))
        if not parsed_files:
            log.warning("No parsed jobs file found — nothing to export")
            return 0
        scored_jobs = json.loads(parsed_files[-1].read_text(encoding="utf-8"))
        log.info(f"Loaded {len(scored_jobs)} jobs from {parsed_files[-1].name}")

    seen_ids = _load_csv_ids(SEEN_CSV)
    rejected_ids = _load_csv_ids(REJECTED_CSV)
    existing_review = _load_review_csv()
    existing_ids = {r["job_id"] for r in existing_review if r.get("job_id")}

    new_jobs = []
    for job in scored_jobs:
        jid = job.get("job_id", "")
        if jid in rejected_ids:
            log.debug(f"Skipping rejected job: {jid}")
            continue
        if jid in existing_ids:
            log.debug(f"Already in review CSV: {jid}")
            # Update last_seen in seen_jobs but don't duplicate in review
            continue
        new_jobs.append(job)

    log.info(f"{len(new_jobs)} new jobs to add to review file")

    if dry_run:
        for j in new_jobs:
            log.info(f"  [DRY RUN] would add: {j.get('company_name')} — {j.get('role_title')} [{j.get('fit_score')}/10]")
        return len(new_jobs)

    # Append new jobs to review CSV
    all_review_rows = existing_review + [
        {k: job.get(k, "") for k in REVIEW_FIELDS}
        for job in new_jobs
    ]
    _save_review_csv(all_review_rows)
    log.info(f"Updated → {REVIEW_CSV.relative_to(BASE_DIR)} ({len(all_review_rows)} total rows)")

    # Update seen_jobs.csv
    _update_seen_csv(scored_jobs)

    # Regenerate Markdown
    _write_review_md(all_review_rows)

    return len(new_jobs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export scored jobs to review files")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    n = run(dry_run=args.dry_run)
    log.info(f"Export done — {n} new jobs added")
