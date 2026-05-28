# Job Radar

A lean local file-based system to track target companies and surface relevant job openings for manual review.

## What it does

1. Reads target companies from `config/target_companies.csv`
2. Fetches career pages (where possible)
3. Parses job listings into structured records
4. Scores jobs 1–10 using keyword-based rules (no LLM required for daily scans)
5. Exports `exports/jobs_for_review.csv` and `exports/jobs_for_review.md` for manual review
6. Waits for manual approval (`approved_for_cv=yes` column)
7. Prepares approved jobs for the existing CV-tailoring workflow

## What it never does

- Send applications
- Contact mentors or write messages
- Tailor CVs without explicit approval
- Invent or embellish experience
- Activate scheduled tasks automatically

## Quick start

```bash
cd ~/Projects/job-radar-claude
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Populate career URLs
python scripts/find_career_urls.py

# Run a scan (dry-run first)
python scripts/run_daily_scan.py --dry-run
python scripts/run_daily_scan.py

# Review exports/jobs_for_review.csv
# Mark approved_for_cv=yes on roles you want to pursue

# Prepare approved jobs
python scripts/prepare_approved_jobs.py
```

## Folder structure

```
job-radar-claude/
├── config/
│   ├── target_companies.csv      ← edit to add/remove companies
│   ├── profile_context.md        ← your skills and positioning
│   ├── scoring_rules.md          ← how fit scores are calculated
│   ├── location_rules.md         ← geographic preferences
│   ├── workflow_rules.md         ← system rules and manual gates
│   └── cv_workflow_integration.md← how to call your CV workflow
├── data/
│   ├── raw/manual/               ← drop manual job JSON files here
│   ├── parsed/                   ← intermediate parsed JSON
│   ├── seen_jobs.csv             ← deduplication tracking
│   ├── rejected_jobs.csv         ← rejected job log
│   └── approved_jobs.csv         ← approved job log
├── exports/
│   ├── jobs_for_review.csv       ← REVIEW THIS daily
│   ├── jobs_for_review.md        ← formatted view
│   └── daily_summary.md          ← scan summary
├── scripts/
│   ├── run_daily_scan.py         ← main orchestrator
│   ├── find_career_urls.py       ← populate missing URLs
│   ├── fetch_jobs.py             ← HTTP fetch career pages
│   ├── parse_jobs.py             ← parse HTML + manual JSON
│   ├── score_jobs.py             ← keyword-based scoring
│   ├── export_review_csv.py      ← write review CSV + Markdown
│   ├── prepare_approved_jobs.py  ← package approved jobs
│   └── setup_launchd.sh          ← macOS scheduler setup (manual activation)
└── docs/
    ├── operating_manual.md
    ├── source_characterization.md
    ├── telegram_integration_plan.md
    └── google_sheets_future_integration.md
```

## Manual job entries

When a career page cannot be scraped, add a JSON file to `data/raw/manual/`:

```json
[
  {
    "company_name": "Wiz",
    "role_title": "Data Engineer",
    "location": "Tel Aviv",
    "work_model": "hybrid",
    "job_url": "https://www.wiz.io/careers/...",
    "description": "Full job description text here..."
  }
]
```

Name the file anything (e.g., `wiz_20260101.json`). It will be picked up on the next scan.

## Dependencies

| Package | Why |
|---------|-----|
| `requests` | HTTP fetching of career pages — stdlib urllib lacks reliable redirect/cookie handling |
| `beautifulsoup4` | HTML parsing of job listing pages — stdlib html.parser has no selector API |
| `python-dotenv` | Load optional config from `.env` — avoids hardcoding paths or tokens |

All other logic uses Python standard library.

## Scheduling

To set up automatic daily runs:
```bash
bash scripts/setup_launchd.sh
# Then review the plist and manually activate with launchctl load
```

See `docs/operating_manual.md` section 5 for full instructions.

## Future

- Per-company HTML/API parsers (see `docs/source_characterization.md`)
- Telegram notifications (see `docs/telegram_integration_plan.md`)
- Google Sheets sync (see `docs/google_sheets_future_integration.md`)
