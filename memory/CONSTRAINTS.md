# CONSTRAINTS.md

Persistent rules and user preferences that govern all work in this project.

---

## Absolute prohibitions (from CLAUDE.md)
- Never send job applications
- Never contact recruiters or mentors
- Never draft mentor messages
- Never tailor CVs without `approved_for_cv=yes` explicitly set in jobs_for_review.csv
- Never invent, embellish, or imply experience that doesn't exist
- Never install or activate the launchd scheduler automatically
- Never commit .env, credentials, or secret files
- Never add a web app (Flask, FastAPI, etc.)
- Never add a database (SQLite, Postgres, etc.) unless explicitly requested
- Never auto-approve jobs — manual gate must always be preserved
- Never remove or bypass the `approved_for_cv` gate

## v1 architecture boundaries
- Storage: local CSV files only
- UI: command-line scripts only
- Scheduling: user activates manually via `launchctl`
- CV tailoring: separate workflow, called manually after `prepare_approved_jobs.py`
- Telegram and Google Sheets: documented only, not implemented

## Code style constraints
- Python standard library preferred; justify any new dependency in README.md
- All scripts must be idempotent
- All file-writing scripts must support `--dry-run`
- Use `logging` module — no inline `print` in library functions
- No hard-coded absolute paths — use `Path(__file__).parent.parent` for BASE_DIR
- No LLM calls in the daily scan path

## Git constraints
- Never create commits automatically
- Never run `git commit` unless explicitly instructed
- After file changes: always show `git status --short`, summary of changes, and checks performed
- User decides when to commit

## Memory constraints
- Never store secrets, tokens, passwords, private keys, or sensitive personal data in memory files
- Keep updates minimal and factual
- Mark uncertain items as Unverified
