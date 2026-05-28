# CLAUDE.md — Job Radar Project Rules

This file governs how Claude Code should behave in this project.
Read this before taking any action.

---

## Core Rules

### Never do these
- Send job applications (ever, under any circumstances)
- Contact recruiters or mentors
- Write or draft mentor messages
- Tailor CVs without an explicit `approved_for_cv=yes` row being present
- Invent, embellish, or imply experience that doesn't exist
- Install or activate scheduled tasks automatically
- Commit `.env`, credentials, or secret files to git
- Add a web app (Flask, FastAPI, etc.)
- Add a database (SQLite, Postgres, etc.) unless explicitly requested

### Default behavior
- Code-first: prefer Python scripts over prompts
- No LLM calls in the daily scan path — keep it deterministic
- Keep outputs concise: one-line log entries, short summaries
- Keep requirements.txt minimal — explain any new dependency in README.md
- Never auto-approve jobs — the manual gate must always be preserved
- Never remove or bypass the `approved_for_cv` gate

### Ask only when something blocks implementation
If a requirement is ambiguous but does not block writing code, create a TODO comment and continue.
Only ask a question when you cannot proceed without an answer.

---

## Architecture Constraints

### v1 boundaries (do not cross without explicit user instruction)
- Storage: local CSV files only (no database)
- UI: command-line scripts only (no web interface)
- Scheduling: user activates manually via `launchctl` (never auto-activate)
- CV tailoring: separate workflow, called manually after `prepare_approved_jobs.py`
- Telegram: documented in `docs/telegram_integration_plan.md` but not implemented
- Google Sheets: documented in `docs/google_sheets_future_integration.md` but not implemented

### File roles
| File | Role |
|------|------|
| `config/target_companies.csv` | Source of truth for companies |
| `exports/jobs_for_review.csv` | Source of truth for job review state |
| `data/seen_jobs.csv` | Dedup — never modify approvals here |
| `data/rejected_jobs.csv` | Reject log — minimal fields only |
| `data/approved_jobs.csv` | Approval log |

### Manual gates that must never be automated
1. Filling missing career URLs (manual edit to target_companies.csv)
2. Marking `approved_for_cv=yes` (manual edit to jobs_for_review.csv)
3. Running `prepare_approved_jobs.py` (manual command)
4. Running the CV workflow (manual command, separate project)
5. Submitting applications (always 100% manual)

---

## Code Style

- Python standard library preferred; only add packages for genuine need
- Scripts are idempotent — safe to run multiple times
- `--dry-run` flag on all scripts that write files
- Log to `logs/daily_scan.log` using the `logging` module
- No inline print statements in library functions (use `logging`)
- No hard-coded absolute paths — use `Path(__file__).parent.parent` for `BASE_DIR`

---

## Scoring
- v1 uses keyword matching only — no LLM
- Score range: 1–10 integer
- Source of truth for scoring logic: `config/scoring_rules.md`
- Add TODO markers where future Claude analysis could improve accuracy
- Never auto-reject based on score — surface everything to review file

---

## When in doubt
- Prefer doing less over doing more
- Prefer a TODO over guessing at a requirement
- Prefer editing existing files over creating new ones
- Never overbuild for hypothetical future needs
