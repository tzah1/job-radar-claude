# DECISIONS.md

Chronological log of real architectural and workflow decisions.

---

## 2026-05-28 — v1 scope locked: CSV-only storage, CLI-only UI
No database, no web interface. All state lives in local CSV files. All user interaction via command-line scripts. Rationale: minimize complexity for a solo, local-first tool.

## 2026-05-28 — No LLM in daily scan path
Scoring is deterministic keyword-matching only (score 1–10). LLM analysis is a future enhancement (TODO markers in code). Rationale: keep the pipeline fast, free, and auditable.

## 2026-05-28 — Manual gates preserved for all approval steps
Five explicit manual gates (career URL entry, approved_for_cv marking, prepare_approved_jobs, CV workflow, application submission) must never be automated. Rationale: user retains full control over job pursuit decisions.

## 2026-05-28 — Scheduler not auto-activated
`setup_launchd.sh` generates the plist but does not load it. User activates via `launchctl load` when ready.

## 2026-05-28 — `uv` required as Python runtime
Plain `python3` is broken on this machine (pyexpat/libexpat mismatch). All commands use `uv run --python venv/bin/python3 python scripts/<script>.py`.
