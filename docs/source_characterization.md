# Source Characterization — Career Page Scraping Notes

## V1 Strategy

**Primary path**: Best-effort automated discovery runs on every daily scan.
For each company with a career URL, the scanner fetches the page, detects the ATS (if any),
and calls the ATS API or parses HTML links. Results land in `exports/jobs_for_review.csv`.

**Manual fallback**: When a source cannot be parsed automatically — or when you find a job
via direct browsing — place a JSON file in `data/raw/manual/`. It flows through the same
parse → score → export pipeline.

**The checklist in `exports/daily_summary.md`** is visibility only.
Primary action is to review `exports/jobs_for_review.csv`, not to open 20 career pages manually.

---

## Current ATS Support (v1)

| ATS | Method | Status |
|-----|--------|--------|
| Greenhouse | Public JSON API (`boards-api.greenhouse.io/v1/boards/{slug}/jobs`) | ✅ Working |
| Lever | Public JSON API (`api.lever.co/v0/postings/{slug}?mode=json`) | ✅ Implemented, needs confirmed slug |
| Ashby | Public JSON API (`api.ashbyhq.com/posting-api/job-board/{slug}`) | ✅ Implemented, needs confirmed slug |
| Comeet | Embedded JSON in careers page HTML | ✅ Implemented |
| Workday | JS-rendered — requires headless browser | ⚠️ source_needs_characterization |
| Workable | JS widget — requires headless browser or API key | ⚠️ source_needs_characterization |
| SmartRecruiters | JS-rendered | ⚠️ source_needs_characterization |
| Unknown / custom | Generic HTML link extraction (fallback) | ⚠️ Low yield |

**Important**: Even for supported ATS platforms, slug extraction from the HTML can fail if the
career page uses a JS-rendered embed. When that happens, status = `source_needs_characterization`
and the company appears in the daily checklist for manual follow-up.

---

## Per-Company Status

| Company | Career URL | ATS | Notes |
|---------|-----------|-----|-------|
| Tenable | tenable.com/careers | Greenhouse | ✅ Working — slug=tenableinc, ~60 jobs/run |
| Zenity | zenity.io/careers | Comeet | ✅ Working — embedded JSON extraction |
| Eleos Health | eleos.health/career/ | Greenhouse | ⚠️ Slug is a UUID/embed key — real slug unknown |
| Mixtiles | mixtiles.com/careers | Greenhouse | ⚠️ Slug resolves to "embed" — real slug unknown |
| Oasis | oasis.security/careers | Greenhouse | ⚠️ Slug resolves to "embed" — real slug unknown |
| Palo Alto Networks | paloaltonetworks.com/company/careers | Workday | ⚠️ JS-rendered — needs characterization |
| Fireblocks | fireblocks.com/careers | Unknown | ℹ️ Fetches OK, no jobs via generic HTML |
| Forter | forter.com/careers/ | Unknown | ℹ️ Fetches OK, no jobs via generic HTML |
| ControlUp | controlup.com/company/careers/ | Unknown | ℹ️ Fetches OK, no jobs via generic HTML |
| Lemonade | makers.lemonade.com/ | Unknown | ℹ️ Fetches OK, no jobs via generic HTML |
| Wiz | wiz.io/careers | Unknown | ℹ️ Fetches OK, no jobs via generic HTML |
| Cyara | cyara.com/careers/ | Unknown | ℹ️ Fetches OK, no jobs via generic HTML |
| Dream Security | dreamgroup.com/careers/ | Unknown | ℹ️ Fetches OK, no jobs via generic HTML |
| Melio | meliopayments.com/careers | Unknown | ℹ️ Fetches OK, no jobs via generic HTML |
| Imperva | imperva.com/careers/ | Unknown | ℹ️ Fetches OK, no jobs via generic HTML |
| Google | careers.google.com/jobs/results/ | Custom (JS) | ⚠️ JS-heavy — use manual JSON or careers.google.com search |

---

## Future Scraping Adapters (planned — not in v1)

These will be added one at a time once the ATS is confirmed and the slug is known.
Do not implement broad scraping across all sites at once.

### Priority order for next adapters

1. **Resolve missing Greenhouse slugs** (Eleos Health, Mixtiles, Oasis)
   - Check the actual career page source to find the real Greenhouse slug
   - Add it to the `notes` column as `Greenhouse slug=<slug>`
   - Then a small update to `_gh_slug()` in `parse_jobs.py` can read it from notes

2. **Lever** — implement once a company in the list is confirmed on Lever
   - API call is already coded; just needs slug confirmation

3. **Ashby** — same as Lever

4. **Workday** — requires headless browser (Playwright or similar)
   - Do NOT implement in v1. Requires additional dependency approval.

5. **Custom parsers** — for companies with static HTML career pages
   - Add one at a time, only after manual investigation confirms the page structure is stable

---

## How to add a manual job (fallback)

When auto-discovery fails or you find a relevant posting manually:

```json
[
  {
    "company_name": "Wiz",
    "role_title": "Data Engineer",
    "location": "Tel Aviv",
    "work_model": "hybrid",
    "job_url": "https://www.wiz.io/careers/...",
    "description": "Full job description text here — paste from the career page",
    "notes": "Found manually on wiz.io/careers"
  }
]
```

Save as `data/raw/manual/<company>_<date>.json`, then run:
```bash
uv run --python venv/bin/python3 python scripts/run_daily_scan.py
```

The job flows through the same parse → score → export pipeline as auto-discovered jobs.

---
## Last Scan Results (auto-updated 2026-05-28 18:36)

| Company | ATS Detected | Status |
|---------|-------------|--------|
| ControlUp | unknown | scan_ok — 0 relevant jobs |
| Cyara | unknown | scan_ok — 0 relevant jobs |
| Dream Security | unknown | scan_ok — 0 relevant jobs |
| Eleos Health | greenhouse | needs characterization (JS/dynamic) |
| Fireblocks | greenhouse | needs characterization (JS/dynamic) |
| Forter | unknown | scan_ok — 0 relevant jobs |
| Google | unknown | scan_ok — 0 relevant jobs |
| Imperva | unknown | scan_ok — 0 relevant jobs |
| Lemonade | unknown | scan_ok — 0 relevant jobs |
| Melio | unknown | scan_ok — 0 relevant jobs |
| Mixtiles | greenhouse | needs characterization (JS/dynamic) |
| Oasis | greenhouse | needs characterization (JS/dynamic) |
| Palo Alto Networks | workday | needs characterization (JS/dynamic) |
| Tenable | greenhouse | scan_ok — jobs extracted |
| Wiz | unknown | scan_ok — 0 relevant jobs |
| Zenity | comeet | scan_ok — jobs extracted |
