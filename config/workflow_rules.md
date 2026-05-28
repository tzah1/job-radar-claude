# Workflow Rules — Job Radar v1

## Core Principles

### What This System Does
1. Reads target companies from CSV
2. Tries to find or verify career page URLs
3. Scans and collects job postings where possible
4. Parses job information into structured records
5. Scores jobs using keyword-based rules
6. Exports a CSV/Markdown review file for manual review
7. Waits for manual approval
8. Prepares approved jobs for the existing CV-tailoring workflow

### What This System Never Does
- Send applications
- Contact mentors or write mentor messages
- Tailor CVs without explicit approval
- Invent or embellish experience
- Auto-approve or skip the manual review gate
- Require Claude tokens for the daily scan
- Use a database (v1)
- Run a web app (v1)
- Activate scheduled tasks automatically

## Manual Gates

### Gate 1: URL Verification
After running `find_career_urls.py`, review and manually fill any missing career_url values
in `config/target_companies.csv` before expecting fetch results.

### Gate 2: Daily Review
After each daily scan, open `exports/jobs_for_review.csv` and review each row.
Mark `approved_for_cv` column:
- `yes` — proceed to CV tailoring preparation
- `no` — move to rejected_jobs.csv
- (blank) — leave for later review

### Gate 3: CV Preparation
Only after marking `approved_for_cv=yes` and running `scripts/prepare_approved_jobs.py`
will a job folder be created under `data/approved_jobs/`.
The CV workflow is a separate manual step — see `config/cv_workflow_integration.md`.

## Idempotency
All scripts are designed to be safe to run multiple times:
- Deduplication uses `data/seen_jobs.csv` by job_id
- Rejected jobs are tracked in `data/rejected_jobs.csv`
- Re-running the daily scan will not duplicate rows in review files

## Priority Order
Company priority in scans follows CSV row order in `config/target_companies.csv`.
Do not add a numeric priority column — reorder rows instead.

## Manual Job Entries
Place JSON files under `data/raw/manual/` to inject jobs that cannot be scraped.
See `docs/operating_manual.md` for the exact format.
