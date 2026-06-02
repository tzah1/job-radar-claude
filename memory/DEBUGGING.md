# DEBUGGING.md

Known issues, environment quirks, and fix notes.

---

## Python runtime — pyexpat/libexpat mismatch (macOS)
**Status:** Active constraint — not fixed, worked around.
**Symptom:** Running `python3` or `pip3` directly fails due to Homebrew Python's pyexpat/libexpat library mismatch.
**Fix:** Always use `uv` with the project venv:
```bash
uv run --python venv/bin/python3 python scripts/<script>.py
```
Never use plain `python3`, `pip3`, or bare `uv run`.

---

## Companies with no auto-discoverable career pages
**Status:** Known limitation.
- Dfingo — company name unverified, no URL
- Zenzap — no careers page found at zenzap.co
- Neo Security — Neosec acquired by Akamai (2023); unclear if different company intended
- Ocean — ambiguous (ocean.io is B2B prospecting in Copenhagen); confirm which is intended
- Harmony — multiple companies share the name; confirm which one

---

## ATS adapters with unverified slugs
- Lever — implemented in parse_jobs.py but slugs not confirmed for current target companies
- Ashby — implemented in parse_jobs.py but slugs not confirmed

---

## Companies needing characterization
- Eleos Health — missing Greenhouse slug
- Mixtiles — missing Greenhouse slug
- Oasis — missing Greenhouse slug
- Palo Alto Networks — Workday (JS-rendered, low yield)
- Fireblocks — needs characterization
See `docs/source_characterization.md` for details.

---

## test_manual_workflow.py
End-to-end pipeline test that creates a temp job, runs parse→score→export, checks output, then cleans up. Exit code 0 = pass. Does not hit network.
```bash
uv run --python venv/bin/python3 python scripts/test_manual_workflow.py
```
