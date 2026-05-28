# Operating Manual — Job Radar v1

## TODO: Local Python virtual environment

**Current status:**
Homebrew Python 3.14 has a broken pip/ensurepip (native library symbol mismatch).
Homebrew Python 3.12 has working pip, but `python3.12 -m venv` also fails ensurepip during bootstrapping.
All Python scripts pass `py_compile` syntax checks with Python 3.12. Infrastructure is valid.

**Decision:** Do not use `curl/get-pip.py` and do not install packages globally for now.

**Next options (choose one when ready):**
1. `brew reinstall python@3.12` — cleanest fix for the Homebrew build
2. Use [`uv`](https://github.com/astral-sh/uv) — fast, self-contained Python env manager, no pip dependency
3. Use a Docker-based development path for full isolation
4. Keep infrastructure validation separate from Python environment troubleshooting

**Impact on current workflow:**
Scripts cannot be executed until a working venv is available.
All file infrastructure, config, docs, and CSV schemas are fully usable now.

## Contents
1. [First-time setup](#1-first-time-setup)
2. [Edit target companies](#2-edit-target-companies)
3. [Populate career URLs](#3-populate-career-urls)
4. [Run the daily scan manually](#4-run-the-daily-scan-manually)
5. [Set up the daily scheduled run](#5-set-up-the-daily-scheduled-run)
6. [Review jobs_for_review.csv](#6-review-jobs_for_reviewcsv)
7. [Mark approved_for_cv=yes](#7-mark-approved_for_cvyes)
8. [Run prepare_approved_jobs.py](#8-run-prepare_approved_jobspy)
9. [What remains manual](#9-what-remains-manual)
10. [Adding Google Sheets later](#10-adding-google-sheets-later)
11. [Adding Telegram later](#11-adding-telegram-later)

---

## 1. First-time setup

```bash
cd ~/Projects/job-radar-claude

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and review environment variables (optional for v1)
cp .env.example .env
```

---

## 2. Edit target companies

File: `config/target_companies.csv`

Columns:
- `company_name` — exact name used throughout the system
- `career_url` — the company's careers/jobs page URL
- `notes` — any context (e.g., "fintech", "cyber protection")

**Priority**: row order determines company priority. Reorder rows to change priority.
Do not add a numeric priority column.

---

## 3. Populate career URLs

**Option A — auto-fill known URLs:**
```bash
python scripts/find_career_urls.py --dry-run   # preview
python scripts/find_career_urls.py             # write
```

**Option B — verify existing URLs:**
```bash
python scripts/find_career_urls.py --verify
```

After running, open `config/target_companies.csv` and manually fill in any
companies listed under "Needs manual career URL entry".

---

## 4. Run the daily scan manually

```bash
# Activate venv first if using one:
source venv/bin/activate

# Full scan:
python scripts/run_daily_scan.py

# Dry run (no files written):
python scripts/run_daily_scan.py --dry-run

# Single company:
python scripts/run_daily_scan.py --company "Wiz"
```

**Outputs:**
- `exports/jobs_for_review.csv` — new jobs appended
- `exports/jobs_for_review.md` — full formatted review list
- `exports/daily_summary.md` — summary of the run
- `logs/daily_scan.log` — full log

---

## 5. Set up the daily scheduled run

**Step 1 — generate the plist:**
```bash
bash scripts/setup_launchd.sh
```

**Step 2 — review and edit the plist:**
```bash
open ~/Library/LaunchAgents/com.jobradar.dailyscan.plist
```
Edit `Hour` and `Minute` to your preferred daily run time.

**Step 3 — activate when ready:**
```bash
launchctl load ~/Library/LaunchAgents/com.jobradar.dailyscan.plist
```

**To check status:**
```bash
launchctl list | grep jobradar
```

**To deactivate:**
```bash
launchctl unload ~/Library/LaunchAgents/com.jobradar.dailyscan.plist
```

---

## 6. Review jobs_for_review.csv

Open `exports/jobs_for_review.csv` in Numbers, Excel, or any CSV editor.

Columns to focus on:
- `fit_score` — 1–10, higher is better fit
- `fit_summary` — why the score was given
- `risks` — potential gaps or issues
- `role_category` — auto-detected category
- `location` / `work_model` — check fit
- `job_url` — click to view original posting

For a formatted view, open `exports/jobs_for_review.md` in any Markdown viewer.

---

## 7. Mark approved_for_cv=yes

In `exports/jobs_for_review.csv`, set the `approved_for_cv` column:

| Value | Meaning |
|-------|---------|
| `yes` | Proceed to CV tailoring preparation |
| `no`  | Reject — will be moved to rejected_jobs.csv on next run |
| (blank) | Pending review — leave for later |

Save the CSV after editing.

---

## 8. Run prepare_approved_jobs.py

After marking approvals:

```bash
# Preview what will be prepared:
python scripts/prepare_approved_jobs.py --dry-run

# Run for real:
python scripts/prepare_approved_jobs.py
```

**Output per approved job:**
```
data/approved_jobs/<company>_<role>_<date>/
  ├── job-description.md      ← paste full JD here if not auto-fetched
  ├── fit-analysis.md         ← fit score breakdown
  ├── cv-tailoring-input.md   ← input for CV workflow
  └── metadata.json           ← machine-readable metadata
```

Then run your CV tailoring workflow on the folder.
See `config/cv_workflow_integration.md` for integration details.

---

## 9. What remains manual

These steps are always manual and will never be automated:

- **Filling missing career URLs** — verify and paste into target_companies.csv
- **Pasting job descriptions** — when auto-fetch is unavailable, paste into job-description.md
- **Reviewing fit_score** — automated scoring is a signal, not a decision
- **Marking approved_for_cv** — the approval gate is always manual
- **CV tailoring** — the CV workflow is separate
- **Final application submission** — 100% manual
- **Mentor messages** — 100% manual, always written by you personally

---

## 10. Adding Google Sheets later

See `docs/google_sheets_future_integration.md` for the full plan.

Short version:
- v1: local CSV only (current)
- Phase 2: export a read-only Google Sheet copy of jobs_for_review.csv
- Phase 3: full Google Sheets API read/write

Never commit Google credentials to git. Store in `.env` (gitignored).

---

## 11. Adding Telegram later

See `docs/telegram_integration_plan.md` for the full plan.

Short version:
- v1: no Telegram (current)
- Future: send daily_summary.md to Telegram
- Future: approve job IDs from Telegram

Never send applications from Telegram. Approval is informational only.
