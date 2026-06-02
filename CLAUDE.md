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

## Git Rules

- **Do not create commits automatically.**
- Do not run `git commit` unless explicitly instructed by the user.
- You may initialize a git repo if needed (`git init`).
- You may freely run `git status`, `git diff`, and `git log` for review.
- After making any file changes, always show:
  - `git status --short`
  - A summary of what files were changed and why
  - What checks or tests were performed
- The user decides when to commit after manual review.

---

## When in doubt
- Prefer doing less over doing more
- Prefer a TODO over guessing at a requirement
- Prefer editing existing files over creating new ones
- Never overbuild for hypothetical future needs

---

## Claude Project Memory Rules

At session start:
1. Read memory/PROJECT_STATE.md
2. Read memory/NEXT_ACTIONS.md
3. Read memory/DECISIONS.md
4. Read memory/CONSTRAINTS.md
5. Use these files as project context before proposing or editing anything.

During work:
Update project memory after every major interaction.

A "major interaction" means:
- user approves a plan
- user rejects or changes direction
- files are created, updated, moved, or removed
- commands/tests are run and results matter
- a bug or environment issue is discovered
- a workflow decision is made
- project state changes
- next actions change
- user says "add to memory", "remember this", "save this", or similar

Memory update rules:
1. Keep updates minimal and factual.
2. Do not rewrite whole memory files unless explicitly asked.
3. Append to SESSION_LOG.md for chronological changes.
4. Update PROJECT_STATE.md only when current state changed.
5. Update DECISIONS.md only for real decisions.
6. Update NEXT_ACTIONS.md whenever next steps change.
7. Update DEBUGGING.md only for technical issues, commands, failures, fixes, or environment notes.
8. Update CONSTRAINTS.md only for persistent rules or user preferences.
9. Never store secrets, tokens, passwords, private keys, or sensitive personal data.
10. Before finishing any response after a major interaction, check whether memory needs updating.

Explicit memory command:
When the user says "add to memory: X", add X to the correct memory file immediately, unless it contains secrets or unsafe sensitive data. If unsure where it belongs, add it to SESSION_LOG.md and mention that it may need later consolidation.

Before finishing a session:
1. Update memory as needed.
2. Run git status --short.
3. Show memory files changed.
4. Show non-memory files changed.
5. Do not commit.

---

## Shared Knowledge

Before starting work, read the shared guidance when relevant:
- `~/AI-Work/knowledge/CROSS_PROJECT_LESSONS.md`
- `~/AI-Work/knowledge/AGENT_WORKFLOW_RULES.md`
- `~/AI-Work/knowledge/TOOLING_DECISIONS.md`
- `~/AI-Work/playbooks/CLAUDE_CODE_PROJECT_MEMORY.md`

Shared knowledge is guidance, not an override.
**This project's explicit prohibitions (Core Rules section above) take absolute priority over shared guidance.**
This project is a deliberately built custom tool — general guidance about evaluating existing tools before building does not apply retroactively to design decisions already made and recorded in `memory/DECISIONS.md`.
If a shared rule conflicts with the project's purpose or the Core Rules above, follow the project-specific rules.
