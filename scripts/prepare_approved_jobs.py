#!/usr/bin/env python3
"""
prepare_approved_jobs.py - Prepare approved jobs for CV-tailoring workflow

Reads exports/jobs_for_review.csv and processes rows where approved_for_cv=yes
that have NOT yet been prepared (status != prepared_for_cv).

For each approved job, creates:
  data/approved_jobs/<company>_<role_slug>_<date>/
    ├── job-description.md
    ├── fit-analysis.md
    ├── cv-tailoring-input.md
    └── metadata.json

Then updates:
  - exports/jobs_for_review.csv (status → prepared_for_cv)
  - data/approved_jobs.csv (log of prepared jobs)

CV workflow integration:
  See config/cv_workflow_integration.md.
  A TODO placeholder marks where the future CV workflow command should be called.

Usage:
    python scripts/prepare_approved_jobs.py [--dry-run]
"""

import csv
import json
import re
import logging
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
APPROVED_DIR = DATA_DIR / "approved_jobs"
APPROVED_LOG_CSV = DATA_DIR / "approved_jobs.csv"
REVIEW_CSV = EXPORTS_DIR / "jobs_for_review.csv"
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

APPROVED_LOG_FIELDS = ["job_id", "company_name", "role_title", "job_url",
                        "approved_date", "folder_path"]


def slugify(text: str, max_len: int = 30) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:max_len].strip("_")


def make_folder_name(company: str, title: str, date: str) -> str:
    return f"{slugify(company)}_{slugify(title)}_{date}"


def write_job_description(job: dict, folder: Path):
    content = f"""# Job Description

**Company**: {job.get('company_name', '')}
**Role**: {job.get('role_title', '')}
**URL**: {job.get('job_url', '')}
**Location**: {job.get('location', '')}
**Work Model**: {job.get('work_model', '')}
**Category**: {job.get('role_category', '')}
**Sector**: {job.get('detected_sector', '')}

---

## Description

{job.get('description', '_(Description not available — paste from career page)_')}
"""
    (folder / "job-description.md").write_text(content, encoding="utf-8")


def write_fit_analysis(job: dict, folder: Path):
    content = f"""# Fit Analysis

**Job ID**: {job.get('job_id', '')}
**Company**: {job.get('company_name', '')}
**Role**: {job.get('role_title', '')}
**Fit Score**: {job.get('fit_score', '?')}/10

---

## Fit Summary
{job.get('fit_summary', '_(Not available)_')}

## Risks and Gaps
{job.get('risks', '_(None identified by automated scoring)_')}

## Notes
{job.get('notes', '_(None)_')}

---

## Scoring Context
Scored using keyword-based rules (v1 — no LLM).
See `config/scoring_rules.md` for scoring criteria.

<!-- TODO: future Claude analysis step may add deeper fit assessment here -->
"""
    (folder / "fit-analysis.md").write_text(content, encoding="utf-8")


def write_cv_tailoring_input(job: dict, folder: Path):
    content = f"""# CV Tailoring Input

## Role Context
- **Company**: {job.get('company_name', '')}
- **Role title**: {job.get('role_title', '')}
- **Job URL**: {job.get('job_url', '')}
- **Location**: {job.get('location', '')}
- **Work model**: {job.get('work_model', '')}
- **Category**: {job.get('role_category', '')}
- **Sector**: {job.get('detected_sector', '')}

---

## Full Job Description
{job.get('description', '_(Paste full job description here before running CV workflow)_')}

---

## Fit Summary
{job.get('fit_summary', '')}

## Risks / Gaps to Address
{job.get('risks', '')}

---

## Keywords to Reflect
_(Auto-extracted from fit scoring — review and supplement manually)_

{_format_keywords(job)}

---

## Positioning Constraints

These constraints must be respected by the CV workflow — do not override:

1. **Do not invent or embellish experience** — use only what is true
2. **Use existing master CV as the single source of truth**
3. **Maintain positioning**: Data Engineer / Analytics Engineer / AI-enabled data workflows
4. **Sector framing**: emphasize cyber/security data or AI/data angle depending on company
5. **Do not change employment dates or responsibilities** — only emphasis and framing

---

## Notes
{job.get('notes', '')}

---

<!-- ═══════════════════════════════════════════════════════════════════
     CV WORKFLOW INTEGRATION POINT
     TODO: When the CV workflow command is confirmed, call it here.
     Example (replace with actual command):
       python ~/cv-workflow/tailor_cv.py --input <this_folder>/
     See config/cv_workflow_integration.md for full integration plan.
     ═══════════════════════════════════════════════════════════════════ -->
"""
    (folder / "cv-tailoring-input.md").write_text(content, encoding="utf-8")


def _format_keywords(job: dict) -> str:
    from score_jobs import CV_SKILLS, ROLE_HIGH, ROLE_MEDIUM
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    combined = f"{job.get('role_title','')} {job.get('description','')} {job.get('notes','')}".lower()
    found = []
    for kw in (ROLE_HIGH + ROLE_MEDIUM + CV_SKILLS):
        if kw in combined and kw not in found:
            found.append(kw)
    if found:
        return "\n".join(f"- {kw}" for kw in found[:15])
    return "_(None auto-detected — add manually based on job description)_"


def write_metadata(job: dict, folder: Path):
    meta = {
        "job_id": job.get("job_id", ""),
        "company_name": job.get("company_name", ""),
        "role_title": job.get("role_title", ""),
        "role_category": job.get("role_category", ""),
        "detected_sector": job.get("detected_sector", ""),
        "location": job.get("location", ""),
        "work_model": job.get("work_model", ""),
        "job_url": job.get("job_url", ""),
        "fit_score": job.get("fit_score", ""),
        "date_found": job.get("date_found", ""),
        "approved_date": datetime.now().strftime("%Y-%m-%d"),
        "folder": str(folder),
        "status": "prepared_for_cv",
    }
    (folder / "metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def update_approved_log(entries: list):
    existing = []
    if APPROVED_LOG_CSV.exists():
        with open(APPROVED_LOG_CSV, newline="", encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
    existing_ids = {r["job_id"] for r in existing}
    for e in entries:
        if e["job_id"] not in existing_ids:
            existing.append(e)
    with open(APPROVED_LOG_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=APPROVED_LOG_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing)


def run(dry_run: bool = False) -> int:
    if not REVIEW_CSV.exists():
        log.warning("exports/jobs_for_review.csv not found — nothing to process")
        return 0

    with open(REVIEW_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    to_prepare = [
        r for r in rows
        if r.get("approved_for_cv", "").strip().lower() == "yes"
        and r.get("status", "").strip() != "prepared_for_cv"
    ]

    if not to_prepare:
        log.info("No newly approved jobs to prepare.")
        return 0

    log.info(f"Found {len(to_prepare)} job(s) to prepare")
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)

    prepared_entries = []
    today = datetime.now().strftime("%Y-%m-%d")

    for job in to_prepare:
        folder_name = make_folder_name(job["company_name"], job["role_title"], today)
        folder = APPROVED_DIR / folder_name

        log.info(f"  preparing: {job['company_name']} — {job['role_title']} → {folder_name}/")

        if dry_run:
            log.info(f"  [DRY RUN] would create {folder}/")
            continue

        folder.mkdir(parents=True, exist_ok=True)
        write_job_description(job, folder)
        write_fit_analysis(job, folder)
        write_cv_tailoring_input(job, folder)
        write_metadata(job, folder)

        prepared_entries.append({
            "job_id": job["job_id"],
            "company_name": job["company_name"],
            "role_title": job["role_title"],
            "job_url": job.get("job_url", ""),
            "approved_date": today,
            "folder_path": str(folder.relative_to(BASE_DIR)),
        })

        # Update status in rows list
        for r in rows:
            if r["job_id"] == job["job_id"]:
                r["status"] = "prepared_for_cv"

    if not dry_run:
        # Rewrite review CSV with updated statuses
        with open(REVIEW_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=REVIEW_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        if prepared_entries:
            update_approved_log(prepared_entries)
            log.info(f"Prepared {len(prepared_entries)} job package(s) under data/approved_jobs/")

        # ═══════════════════════════════════════════════════════════════════
        # CV WORKFLOW INTEGRATION POINT
        # TODO: After preparing all job folders, optionally call the CV workflow.
        # When the command is confirmed, replace this block:
        #
        # import subprocess
        # for entry in prepared_entries:
        #     cmd = ["python", "~/cv-workflow/tailor_cv.py", "--input", entry["folder_path"]]
        #     subprocess.run(cmd, check=True)
        #
        # See config/cv_workflow_integration.md for the full integration plan.
        # ═══════════════════════════════════════════════════════════════════

    return len(to_prepare)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare approved jobs for CV tailoring")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    n = run(dry_run=args.dry_run)
    if n == 0:
        log.info("Nothing to prepare. Mark rows as approved_for_cv=yes in exports/jobs_for_review.csv first.")
