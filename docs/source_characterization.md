# Source Characterization — Career Page Scraping Notes

This document records per-company career page structure findings.
Update this file as you investigate each company's career page.

Use this to guide implementing company-specific parsers in `scripts/parse_jobs.py`.

---

## Status Legend
- `characterized` — selectors identified, ready to implement
- `dynamic` — heavily JS-rendered, requires manual or API approach
- `api_available` — company exposes a jobs API endpoint
- `manual_only` — scraping impractical, use manual JSON entries
- `not_investigated` — not yet looked at

---

## Companies

### Forter
- **Status**: not_investigated
- **URL**: https://www.forter.com/careers/
- **Notes**: TODO

### ControlUp
- **Status**: not_investigated
- **URL**: https://www.controlup.com/about-us/careers/
- **Notes**: TODO

### Lemonade
- **Status**: not_investigated
- **URL**: https://makers.lemonade.com/
- **Notes**: Uses Greenhouse ATS likely

### Fireblocks
- **Status**: not_investigated
- **URL**: https://www.fireblocks.com/company/careers/
- **Notes**: TODO

### Palo Alto Networks
- **Status**: not_investigated
- **URL**: https://www.paloaltonetworks.com/company/careers
- **Notes**: Large company, likely has structured job API. TODO: check jobs.lever.co or greenhouse

### Tenable
- **Status**: not_investigated
- **URL**: https://www.tenable.com/careers
- **Notes**: TODO

### Eleos Health
- **Status**: not_investigated
- **Notes**: AI for therapy sessions. TODO: find URL and characterize

### Wiz
- **Status**: not_investigated
- **URL**: https://www.wiz.io/careers
- **Notes**: Likely Greenhouse or Lever

### Cyara
- **Status**: not_investigated
- **Notes**: TODO: find URL

### Dream Security
- **Status**: not_investigated
- **Notes**: Cyber protection. TODO: find URL

### Dfingo
- **Status**: not_investigated
- **Notes**: Name uncertain — verify spelling before investigating

### Zenity
- **Status**: not_investigated
- **URL**: https://www.zenity.io/careers/
- **Notes**: TODO

### Mixtiles
- **Status**: not_investigated
- **URL**: https://www.mixtiles.com/careers
- **Notes**: TODO

### Oasis
- **Status**: not_investigated
- **Notes**: TODO: clarify which Oasis (multiple companies with this name)

### Zenzap
- **Status**: not_investigated
- **Notes**: TODO: find URL

### Neo Security
- **Status**: not_investigated
- **Notes**: Name uncertain — verify before investigating

### Melio
- **Status**: not_investigated
- **URL**: https://www.meliopayments.com/careers
- **Notes**: Fintech. TODO

### Imperva
- **Status**: not_investigated
- **URL**: https://www.imperva.com/careers/
- **Notes**: Security/CDN company. TODO

### Ocean
- **Status**: not_investigated
- **Notes**: Data pipelines focus. TODO: find URL. Note: may be ocean.io or different branding

### Harmony
- **Status**: not_investigated
- **Notes**: TODO: clarify which Harmony company

---

## Common ATS Patterns

When a company uses a known ATS, check these URL patterns:

| ATS | URL Pattern | Notes |
|-----|-------------|-------|
| Greenhouse | `boards.greenhouse.io/company` | JSON API available |
| Lever | `jobs.lever.co/company` | JSON API available |
| Workday | `company.wd1.myworkdayjobs.com` | Dynamic, harder to scrape |
| Comeet | `www.comeet.com/jobs/company/` | Israeli companies common |
| TeamTailor | `company.teamtailor.com` | Some have RSS |

### Greenhouse API (high value — implement when confirmed)
```
GET https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs
```
Returns JSON — no HTML parsing needed. Pure data, reliable.

### Lever API (high value — implement when confirmed)
```
GET https://api.lever.co/v0/postings/{company_slug}?mode=json
```
Also returns JSON.

### TODO: For each company using Greenhouse or Lever, implement the API call
instead of HTML scraping. Add fetcher logic in `scripts/fetch_jobs.py` and
parser logic in `scripts/parse_jobs.py`.
