#!/usr/bin/env python3
"""
test_manual_workflow.py - Validate the manual job input pipeline end-to-end

Creates a temporary test job in data/raw/manual/, runs the parse → score → export
pipeline, verifies the job would appear in review output, then removes all temporary
files and CSV entries.

Does NOT make network requests.
Does NOT modify jobs_for_review.csv permanently (uses dry_run export).

Usage:
    uv run --python venv/bin/python3 python scripts/test_manual_workflow.py

Exit code: 0 = all checks passed, 1 = failure
"""

import csv
import io
import json
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

_TEST_FILENAME = "_workflow_test_temp.json"

_TEST_JOB = [
    {
        "company_name": "TEST_COMPANY",
        "role_title": "Test Data Engineer",
        "location": "Tel Aviv",
        "work_model": "hybrid",
        "job_url": "https://test.example.com/job/test-data-engineer",
        "description": (
            "We are looking for a Data Engineer to join the data platform team. "
            "You will design and build scalable data pipelines using Python, Airflow, "
            "dbt, Spark, and Kafka. Experience with SQL and ETL workflows is required. "
            "Hybrid work model from Tel Aviv with flexible hours."
        ),
        "notes": "AUTO_TEST — created by test_manual_workflow.py",
    }
]

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# CSV field lists (mirrors export_review_csv.py and seen_jobs definitions)
_REVIEW_FIELDS = [
    "job_id", "date_found", "company_name", "role_title", "role_category",
    "detected_sector", "location", "work_model", "job_url", "fit_score",
    "fit_summary", "risks", "approved_for_cv", "status", "notes",
]
_SEEN_FIELDS = [
    "job_id", "company_name", "role_title", "job_url",
    "first_seen", "last_seen", "status",
]


def _remove_test_row(path: Path, fields: list, test_id: str) -> None:
    """Remove a row by job_id from a CSV file (in-place)."""
    if not path.exists() or not test_id:
        return
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    cleaned = [r for r in rows if r.get("job_id") != test_id]
    if len(cleaned) < len(rows):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cleaned)
        path.write_text(buf.getvalue(), encoding="utf-8")


def _cleanup(test_json: Path, test_job_id: str | None) -> None:
    """Remove temporary test file and any residual rows from CSV outputs."""
    if test_json.exists():
        test_json.unlink()
    if test_job_id:
        _remove_test_row(
            BASE_DIR / "exports" / "jobs_for_review.csv",
            _REVIEW_FIELDS,
            test_job_id,
        )
        _remove_test_row(
            BASE_DIR / "data" / "seen_jobs.csv",
            _SEEN_FIELDS,
            test_job_id,
        )


def run() -> bool:
    log.info("=" * 55)
    log.info("Manual workflow test — job-radar-claude")
    log.info("=" * 55)

    manual_dir = BASE_DIR / "data" / "raw" / "manual"
    manual_dir.mkdir(parents=True, exist_ok=True)
    test_json = manual_dir / _TEST_FILENAME
    test_job_id: str | None = None

    try:
        # ── Step 1: Write temporary manual job JSON ───────────────────────────
        test_json.write_text(json.dumps(_TEST_JOB, indent=2), encoding="utf-8")
        log.info(f"created   {test_json.relative_to(BASE_DIR)}")

        # ── Step 2: Parse manual files only (no HTML/API calls) ───────────────
        import parse_jobs
        manual_jobs = parse_jobs.parse_manual_jobs()
        test_records = [j for j in manual_jobs
                        if j.get("company_name") == "TEST_COMPANY"]
        if not test_records:
            log.error("FAIL  parse — TEST_COMPANY job not found after parsing")
            return False
        test_job_id = test_records[0]["job_id"]
        log.info(
            f"parsed    job_id={test_job_id}"
            f"  title={test_records[0]['role_title']}"
        )

        # ── Step 3: Score ──────────────────────────────────────────────────────
        import score_jobs
        scored = score_jobs.run(list(test_records), dry_run=True)
        score = scored[0].get("fit_score")
        category = scored[0].get("role_category", "")
        if not score:
            log.error("FAIL  score — fit_score missing after scoring step")
            return False
        log.info(f"scored    {score}/10  category={category}")
        log.info(f"summary   {scored[0].get('fit_summary', '')}")

        # ── Step 4: Export dry-run (verifies logic, writes nothing to disk) ───
        import export_review_csv
        new_count = export_review_csv.run(scored_jobs=scored, dry_run=True)
        if new_count < 1:
            log.error("FAIL  export — job not counted as new in dry-run export")
            return False
        log.info(f"export    dry-run OK — would add {new_count} job(s)")

        # ── All checks passed ──────────────────────────────────────────────────
        log.info("")
        log.info("=" * 55)
        log.info("PASS — manual workflow is working end-to-end")
        log.info("=" * 55)
        log.info("")
        log.info("To add a real job, create a file under data/raw/manual/")
        log.info("and run:  uv run --python venv/bin/python3 python scripts/run_daily_scan.py")
        return True

    except Exception as exc:
        log.exception(f"FAIL — unexpected error: {exc}")
        return False

    finally:
        _cleanup(test_json, test_job_id)
        log.info("")
        log.info(f"cleanup   temp JSON removed, no test rows in exports")


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
