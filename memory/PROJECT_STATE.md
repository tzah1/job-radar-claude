# PROJECT_STATE.md

Last updated: 2026-06-02

## Project
Job Radar — local Python pipeline that scans target company career pages, scores jobs by keyword matching (no LLM), and exports them for manual review.

## Current Phase
v1 — operational. Daily scan pipeline is working end-to-end.

## Key Counts (as of last scan 2026-05-28)
- Target companies: 21 in config (16 with verified career URLs, 5 unresolved)
- Last scan: 2026-05-28 — 52 jobs parsed, 17 new, 3 high-fit (score 8–10)
- Unresolved companies: Dfingo, Zenzap, Neo Security, Ocean, Harmony (no confirmed career URLs)

## Pipeline Status
| Script | Status |
|--------|--------|
| run_daily_scan.py | Working |
| fetch_jobs.py | Working |
| parse_jobs.py | Working (Greenhouse, Comeet confirmed; Lever/Ashby implemented, slugs unverified) |
| score_jobs.py | Working — keyword-only, v1 |
| export_review_csv.py | Working |
| prepare_approved_jobs.py | Working |
| find_career_urls.py | Available for populating missing URLs |
| setup_launchd.sh | Available — scheduler NOT activated |

## ATS Coverage
- Greenhouse: Working
- Comeet: Working
- Lever: Implemented — Unverified (slug confirmation needed)
- Ashby: Implemented — Unverified (slug confirmation needed)
- Workday: Needs characterization
- Others: Generic HTML fallback (low yield)

## Scheduler
macOS launchd plist can be generated via `setup_launchd.sh`. NOT loaded/activated — manual activation required.

## Runtime / Environment
- Python runtime: `uv venv` with Python 3.12 (plain `python3` broken on this machine — pyexpat/libexpat mismatch)
- Always use: `uv run --python venv/bin/python3 python scripts/<script>.py`
- Dependencies: requests, beautifulsoup4, python-dotenv
