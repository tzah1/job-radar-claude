# Google Sheets Integration Plan

**Status**: Not implemented in v1. All I/O uses local CSV files.

---

## Phase 1 — v1 (current): Local CSV only

All data lives on disk:

| File | Purpose |
|------|---------|
| `config/target_companies.csv` | Input: company list |
| `exports/jobs_for_review.csv` | Output: review queue |
| `data/seen_jobs.csv` | Dedup tracking |
| `data/rejected_jobs.csv` | Rejection log |
| `data/approved_jobs.csv` | Approval log |

Edit files directly in Numbers, Excel, or any CSV editor.

**Pros**: No credentials, no internet required, works offline  
**Cons**: Not accessible from phone or other devices

---

## Phase 2 — Read-only Google Sheet export

**Concept**: After each daily scan, publish `exports/jobs_for_review.csv`
to a Google Sheet for easy viewing on mobile.

This is **one-way only**: Google Sheets is a view, the CSV is the source of truth.

Implementation:
1. Enable Google Sheets API in Google Cloud Console
2. Create a service account and download `credentials.json`
3. Store `credentials.json` path in `.env` as `GOOGLE_CREDENTIALS_PATH`
4. Store the target sheet ID in `.env` as `GOOGLE_SHEET_ID`
5. Add `scripts/sync_to_sheets.py`:
   - Reads `exports/jobs_for_review.csv`
   - Overwrites the "Jobs" tab in the Google Sheet
   - Called optionally from `run_daily_scan.py` (gated by env var)

```python
# Pseudocode
from google.oauth2 import service_account
from googleapiclient.discovery import build

def sync_review_to_sheets(csv_path, credentials_path, sheet_id):
    creds = service_account.Credentials.from_service_account_file(credentials_path)
    service = build("sheets", "v4", credentials=creds)
    # Clear and rewrite the jobs tab
    ...
```

**Packages needed** (do not add until implementing):
- `google-auth` — authentication
- `google-auth-oauthlib` — OAuth flow
- `google-api-python-client` — Sheets API

---

## Phase 3 — Full read/write Google Sheets integration

**Concept**: Use Google Sheets as the primary review interface.  
Read `approved_for_cv` column from Sheets back into the local workflow.

This creates a two-way sync:
- Daily scan writes new jobs to Sheets
- You edit `approved_for_cv` column in Sheets from any device
- `prepare_approved_jobs.py` reads approvals from Sheets (not local CSV)

Implementation additions:
1. `sync_from_sheets.py` — pull latest Sheet data into local `jobs_for_review.csv`
2. Run `sync_from_sheets.py` before `prepare_approved_jobs.py`
3. Conflict resolution: Sheet wins (it is the source of truth for approvals in this phase)

---

## Security Considerations

**Never commit credentials to git.** This is critical.

1. All credential files go in `.env` path references only — the actual files are NOT in the project directory, or are placed in a gitignored location
2. `.gitignore` already excludes `credentials.json`, `*.json.key`, `service_account*.json`, `google_credentials*.json`
3. Use a **service account** with minimal permissions (only the specific Sheet, read/write only)
4. Do not use your personal Google account OAuth tokens in scripts
5. Rotate credentials if ever accidentally committed or exposed
6. Add the Google Sheet as "restricted" (not public) in sharing settings

**Checklist before activating Google Sheets integration**:
- [ ] `credentials.json` is NOT in the project directory
- [ ] `GOOGLE_CREDENTIALS_PATH` points to a location outside the git repo (e.g., `~/.config/job-radar/`)
- [ ] `git status` shows no credential files
- [ ] Service account has only the specific sheet scoped

---

## Switching Between Phases

The input/output layer in v1 is designed to make phase transitions easy:

- `export_review_csv.py` writes the CSV — replace this with a Sheets writer for Phase 2
- `prepare_approved_jobs.py` reads the CSV — replace the read call with a Sheets reader for Phase 3
- All internal logic (scoring, dedup, parsing) is unchanged across phases
