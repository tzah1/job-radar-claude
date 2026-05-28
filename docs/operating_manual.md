# Operating Manual — Job Radar v1

## Python Runtime — Working Setup

**Status: resolved.** Runtime works via `uv` with its own managed CPython 3.12.13.

### Why uv instead of plain python3/pip
Homebrew Python 3.12 and 3.14 both have a broken `pyexpat`/`libexpat` symbol mismatch that crashes pip during any install operation. `uv` bypasses this entirely by using its own downloaded CPython build.

> **Important:** Do not use plain `python3`, `pip3`, or bare `uv run` on this machine. Always use the explicit `--python venv/bin/python3` flag until global Python is repaired.

### One-time setup (already done — for reference)
```bash
brew install uv
uv venv --python python3.12 venv
uv pip install --python venv/bin/python3 -r requirements.txt
```

### Verified working run command
```bash
uv run --python venv/bin/python3 python scripts/run_daily_scan.py --dry-run
```

### Alternative after activating venv
```bash
source venv/bin/activate
python scripts/run_daily_scan.py --dry-run
deactivate
```

### TODO: Global Python repair (separate future task)
Homebrew Python is broken due to a `libexpat` version mismatch (`_XML_SetAllocTrackerActivationThreshold` missing from `/usr/lib/libexpat.1.dylib`). Fix options when ready:
1. `brew reinstall python@3.12` — likely fixes the build linkage
2. `brew reinstall expat` followed by `brew reinstall python@3.12`
3. macOS system update may resolve the underlying library version gap

Do not attempt this repair during active job-radar work sessions.

## Git Rules

- **Do not create commits automatically.**
- Do not run `git commit` unless explicitly instructed by the user.
- You may run `git status`, `git diff`, and `git log` freely for review.
- After any file changes, Claude should show:
  - `git status --short`
  - Summary of changed files
  - What checks were performed
- The user decides when to commit after manual review.

---

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
cd ~/AI-Work/projects/job-radar-claude

# Install uv (once, if not already installed)
brew install uv

# Create venv using uv's managed Python 3.12
uv venv --python python3.12 venv

# Install dependencies
uv pip install --python venv/bin/python3 -r requirements.txt

# Copy and review environment variables (optional for v1)
cp .env.example .env
```

> Note: Do not use `python3 -m venv` or `pip install` directly — global Python is broken on this machine. See the **Python Runtime** section above.

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

**Preferred (no activation needed):**
```bash
uv run --python venv/bin/python3 python scripts/run_daily_scan.py --dry-run
uv run --python venv/bin/python3 python scripts/run_daily_scan.py
uv run --python venv/bin/python3 python scripts/run_daily_scan.py --company "Wiz"
```

**Alternative (activate venv first):**
```bash
source venv/bin/activate
python scripts/run_daily_scan.py --dry-run
python scripts/run_daily_scan.py
python scripts/run_daily_scan.py --company "Wiz"
deactivate
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
uv run --python venv/bin/python3 python scripts/prepare_approved_jobs.py --dry-run

# Run for real:
uv run --python venv/bin/python3 python scripts/prepare_approved_jobs.py
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
