# Operating Manual — Job Radar v1

## Python Runtime — Working Setup

**Status: resolved.** Runtime works via `uv` with its own managed CPython 3.12.

### Why uv instead of plain python3
Homebrew Python 3.12 and 3.14 both have a broken `pyexpat`/`libexpat` symbol mismatch
that crashes pip during any install operation. `uv` bypasses this by using its own
downloaded CPython build.

> **Important:** Do not use plain `python3`, `pip3`, or bare `uv run`.
> Always use `--python venv/bin/python3` until global Python is repaired.

### One-time setup (already done — for reference)
```bash
brew install uv
uv venv --python python3.12 venv
uv pip install --python venv/bin/python3 -r requirements.txt
```

### Verified working commands
```bash
# Dry run — validates pipeline, writes nothing
uv run --python venv/bin/python3 python scripts/run_daily_scan.py --dry-run

# Real run
uv run --python venv/bin/python3 python scripts/run_daily_scan.py

# Single company
uv run --python venv/bin/python3 python scripts/run_daily_scan.py --company "Wiz"
```

### TODO: Global Python repair (separate future task)
Homebrew Python is broken due to a `libexpat` version mismatch. Do not attempt this
during active job-radar work sessions. Options when ready:
1. `brew reinstall python@3.12`
2. `brew reinstall expat` then `brew reinstall python@3.12`
3. macOS system update may resolve the library gap

---

## Git Rules

- **Do not create commits automatically.**
- Do not run `git commit` unless explicitly instructed by the user.
- You may run `git status`, `git diff`, and `git log` freely for review.
- After any file changes, show `git status --short` and a summary of what changed.
- The user decides when to commit after manual review.

---

## Contents
1. [First-time setup](#1-first-time-setup)
2. [Edit target companies](#2-edit-target-companies)
3. [Populate career URLs](#3-populate-career-urls)
4. [Run the daily scan manually](#4-run-the-daily-scan-manually)
5. [Manual web scan workflow](#5-manual-web-scan-workflow)
6. [Test the manual workflow script](#6-test-the-manual-workflow-script)
7. [Set up the daily scheduled run](#7-set-up-the-daily-scheduled-run)
8. [Review jobs_for_review.csv](#8-review-jobs_for_reviewcsv)
9. [Mark approved_for_cv=yes](#9-mark-approved_for_cvyes)
10. [Run prepare_approved_jobs.py](#10-run-prepare_approved_jobspy)
11. [Runtime outputs and Git](#11-runtime-outputs-and-git)
12. [What remains manual](#12-what-remains-manual)
13. [Adding Google Sheets later](#13-adding-google-sheets-later)
14. [Adding Telegram later](#14-adding-telegram-later)

---

## 1. First-time setup

```bash
cd ~/AI-Work/projects/job-radar-claude

brew install uv
uv venv --python python3.12 venv
uv pip install --python venv/bin/python3 -r requirements.txt

# Optional — review environment variables
cp .env.example .env
```

> Do not use `python3 -m venv` or `pip install` — global Python is broken. See
> the **Python Runtime** section above.

---

## 2. Edit target companies

File: `config/target_companies.csv`

Columns:
- `company_name` — exact name used throughout the system
- `career_url` — the company's careers/jobs page URL
- `notes` — context (e.g., "fintech", "Greenhouse slug=tenableinc")

Row order = priority order. Do not add a numeric priority column.

Companies with a blank `career_url` are skipped during auto-fetch but still appear in
the daily checklist so you can check them manually when the URL is resolved.

---

## 3. Populate career URLs

**Option A — auto-fill known URLs:**
```bash
uv run --python venv/bin/python3 python scripts/find_career_urls.py --dry-run
uv run --python venv/bin/python3 python scripts/find_career_urls.py
```

**Option B — verify existing URLs:**
```bash
uv run --python venv/bin/python3 python scripts/find_career_urls.py --verify
```

After running, manually fill in any companies still listed as needing a URL.

---

## 4. Run the daily scan manually

```bash
# Dry run first — recommended before every real run
uv run --python venv/bin/python3 python scripts/run_daily_scan.py --dry-run

# Real run
uv run --python venv/bin/python3 python scripts/run_daily_scan.py

# Single company (useful for debugging)
uv run --python venv/bin/python3 python scripts/run_daily_scan.py --company "Wiz"
```

**Outputs written:**
- `exports/jobs_for_review.csv` — new jobs appended (approved rows never overwritten)
- `exports/jobs_for_review.md` — full formatted review list
- `exports/daily_summary.md` — scan summary + career page checklist
- `logs/daily_scan.log` — full log

**None of these are committed to git.** See section 11.

---

## 5. Manual web scan workflow

Use this when auto-discovery finds nothing for a company, or when you spot a relevant
role while browsing.

### Step-by-step

**1. Open the career URL.**

Find it in `config/target_companies.csv`. The `exports/daily_summary.md` also lists
all career URLs as a fallback checklist.

**2. Search for relevant roles such as:**
- Data Engineer, Analytics Engineer, Data Analyst
- AI Operations, Data Operations, AI Engineer
- Security Data, Big Data
- Solutions Engineer, Platform Engineer (if data-adjacent)

**3. Create a JSON file under `data/raw/manual/`.**

Filename convention: `<company>_<role>_<YYYYMMDD>.json`

Example — `data/raw/manual/wiz_data_engineer_20260528.json`:
```json
[
  {
    "company_name": "Wiz",
    "role_title": "Data Engineer",
    "location": "Tel Aviv",
    "work_model": "Hybrid",
    "job_url": "https://www.wiz.io/careers/data-engineer/...",
    "description": "Paste the full job description here.",
    "notes": "Manual capture from wiz.io/careers"
  }
]
```

Required fields: `company_name`, `role_title`.
Optional but improve scoring: `location`, `work_model`, `description`, `notes`.

Multiple jobs in one file — just add more objects to the array:
```json
[
  { "company_name": "Wiz", "role_title": "Data Engineer", ... },
  { "company_name": "Wiz", "role_title": "Analytics Engineer", ... }
]
```

**4. Run the daily scan:**
```bash
uv run --python venv/bin/python3 python scripts/run_daily_scan.py
```

**5. Review the output:**
```bash
open exports/jobs_for_review.csv   # Numbers / Excel
# or
cat exports/jobs_for_review.md
```

**6. Mark roles you want to pursue:**
In `exports/jobs_for_review.csv`, set `approved_for_cv=yes` for the row. Save the file.

**7. Prepare the approved CV package:**
```bash
uv run --python venv/bin/python3 python scripts/prepare_approved_jobs.py
```

---

## 6. Test the manual workflow script

Validates the full parse → score → export chain without making any network requests
and without leaving test data in the review outputs.

```bash
uv run --python venv/bin/python3 python scripts/test_manual_workflow.py
```

Expected output:
```
INFO  created   data/raw/manual/_workflow_test_temp.json
INFO  parsed    job_id=xxxxxxxxxxxx  title=Test Data Engineer
INFO  scored    9/10  category=Data Engineering
INFO  export    dry-run OK — would add 1 job(s)
INFO  PASS — manual workflow is working end-to-end
INFO  cleanup   temp JSON removed, no test rows in exports
```

Exit code 0 = pass, 1 = failure.

---

## 7. Set up the daily scheduled run

**Step 1 — test manually first (section 4).**
Run the daily scan by hand and confirm it works before scheduling.

**Step 2 — generate the plist:**
```bash
bash scripts/setup_launchd.sh
```

**Step 3 — review and edit the run time:**
```bash
open ~/Library/LaunchAgents/com.jobradar.dailyscan.plist
```
Edit `<key>Hour</key>` and `<key>Minute</key>` to your preferred daily run time.

**Step 4 — activate when ready:**
```bash
launchctl load ~/Library/LaunchAgents/com.jobradar.dailyscan.plist
```

**Check status:**
```bash
launchctl list | grep jobradar
```

**View logs:**
```bash
tail -f logs/daily_scan.log          # main scan log
tail -f logs/launchd_stdout.log      # stdout captured by launchd
tail -f logs/launchd_stderr.log      # stderr/errors captured by launchd
```

**Verify a scheduled run happened:**
```bash
# Check the timestamp on the log file
ls -lh logs/daily_scan.log

# Check the summary
cat exports/daily_summary.md
```

**Deactivate:**
```bash
launchctl unload ~/Library/LaunchAgents/com.jobradar.dailyscan.plist
```

**Remove plist entirely:**
```bash
launchctl unload ~/Library/LaunchAgents/com.jobradar.dailyscan.plist
rm ~/Library/LaunchAgents/com.jobradar.dailyscan.plist
```

---

## 8. Review jobs_for_review.csv

Open `exports/jobs_for_review.csv` in Numbers, Excel, or any CSV editor.
For a formatted view, open `exports/jobs_for_review.md` in any Markdown viewer.

Columns to focus on:

| Column | What to look for |
|--------|-----------------|
| `fit_score` | 1–10 — higher is better fit |
| `fit_summary` | Why the score was given |
| `risks` | Potential gaps or mismatches |
| `role_category` | Auto-detected category |
| `location` / `work_model` | Check geographic and work-model fit |
| `job_url` | Click to view original posting |

---

## 9. Mark approved_for_cv=yes

In `exports/jobs_for_review.csv`, set the `approved_for_cv` column:

| Value | Meaning |
|-------|---------|
| `yes` | Proceed to CV tailoring preparation |
| `no` | Reject — will be skipped on next run |
| _(blank)_ | Pending review |

Save the CSV after editing.

---

## 10. Run prepare_approved_jobs.py

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

## 11. Runtime outputs and Git

The following files are **generated by every scan** and are excluded from git via
`.gitignore`. They live on disk but should never be committed:

```
exports/jobs_for_review.csv
exports/jobs_for_review.md
exports/daily_summary.md
data/seen_jobs.csv
data/rejected_jobs.csv
data/raw/*/           (fetched HTML dirs)
data/parsed/          (intermediate parsed JSON)
logs/*.log
```

**These are working files, not source files.** They are regenerated on every run.
Committing them would create false diffs on every scan.

To verify these are properly excluded:
```bash
git status --short   # they should not appear (or appear as ?? and be ignored)
```

---

## 12. What remains manual

These steps are always manual and will never be automated:

- **Filling missing career URLs** — verify and paste into target_companies.csv
- **Web scan for companies that failed auto-discovery** — open career page manually
- **Pasting job descriptions** — when auto-fetch is unavailable, paste into JSON file
- **Reviewing fit_score** — automated scoring is a signal, not a decision
- **Marking approved_for_cv** — the approval gate is always manual
- **CV tailoring** — the CV workflow is separate and manual
- **Final application submission** — 100% manual
- **Mentor messages** — 100% manual, always written personally

---

## 13. Adding Google Sheets later

See `docs/google_sheets_future_integration.md` for the full plan.

Short version:
- v1: local CSV only (current)
- Phase 2: export a read-only Google Sheet copy of jobs_for_review.csv
- Phase 3: full Google Sheets API read/write

Never commit Google credentials to git. Store in `.env` (gitignored).

---

## 14. Adding Telegram later

See `docs/telegram_integration_plan.md` for the full plan.

Short version:
- v1: no Telegram (current)
- Future: send daily_summary.md to Telegram
- Future: approve job IDs from Telegram

Never send applications from Telegram. Approval is informational only.
