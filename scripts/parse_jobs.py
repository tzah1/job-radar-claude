#!/usr/bin/env python3
"""
parse_jobs.py - Parse career pages and manual entries into structured job records

Sources (in priority order):
  1. data/raw/manual/*.json         — manually entered job descriptions
  2. data/raw/<company>/*.html      — fetched HTML, dispatched by ATS type

ATS support:
  - Greenhouse  → JSON API (boards-api.greenhouse.io)
  - Lever       → JSON API (api.lever.co)
  - Ashby       → JSON API (api.ashbyhq.com)
  - Comeet      → HTML fetch + parse (comeet.com/jobs/...)
  - Workday / Workable / SmartRecruiters → marked source_needs_characterization
  - Unknown     → generic HTML link extraction fallback

Relevance filtering:
  Clearly non-technical business roles (sales, HR, legal, admin, pure marketing)
  are dropped. Everything else is included — scoring handles prioritisation.

Per-company status (available via get_run_stats() after run()):
  scan_ok | no_jobs_found | source_needs_characterization | parse_error | no_html_file

Usage:
    python scripts/parse_jobs.py [--dry-run]
    Importable: run(dry_run) -> list[dict]
              get_run_stats() -> dict
"""

import re
import csv
import json
import time
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
MANUAL_DIR = RAW_DIR / "manual"
PARSED_DIR = DATA_DIR / "parsed"
LOG_FILE = BASE_DIR / "logs" / "daily_scan.log"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

ATS_DELAY = 1.5   # seconds between secondary ATS API calls (politeness)
REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Relevance filter ──────────────────────────────────────────────────────────
# Strong signals → always include
RELEVANT_STRONG = [
    "data engineer", "analytics engineer", "data analyst",
    "data engineering", "analytics engineering",
    "ai engineer", "ai ops", "aiops", "ml engineer", "mlops", "ml ops",
    "data platform", "data infrastructure", "data pipeline",
    "data ops", "dataops", "data operations", "data architect",
    "big data", "etl engineer", "etl developer", "data integration",
    "data science", "data scientist",
    "bi engineer", "business intelligence engineer",
    "security data", "log analysis", "siem",
]

# Weak signals → include unless excluded
RELEVANT_WEAK = [
    "backend engineer", "backend developer",
    "platform engineer", "cloud engineer", "infrastructure engineer",
    "solutions engineer", "technical lead", "tech lead",
    "devops", "site reliability", "sre",
    "security engineer", "security researcher", "security analyst",
    "security architect", "application security",
    "machine learning", "artificial intelligence",
    "python developer", "python engineer",
    "r&d engineer", "research engineer",
    "software engineer", "software developer",  # broad but score will sort
]

# Clear exclusions → always skip
EXCLUDED = [
    "frontend developer", "frontend engineer", "front-end developer",
    "front-end engineer", "front end developer", "ui developer", "ui engineer",
    "react developer", "react engineer", "angular developer", "vue developer",
    "mobile developer", "ios developer", "android developer", "flutter",
    "account executive", "account manager",
    "sales development representative", "inside sales", "sales representative",
    "business development representative",
    "recruiter", "talent acquisition", "head of people",
    "human resources", "hr manager", "hr generalist", "hr business partner",
    "legal counsel", "attorney", "general counsel",
    "graphic designer", "ux/ui", "product designer",
    "office manager", "executive assistant",
    "social media manager", "social media specialist",
    "marketing manager", "marketing specialist", "content writer",
    "finance manager", "controller", "accountant", "bookkeeper",
]

# Technical title signals (fallback for anything not matched above)
_TECH_SIGNALS = ["engineer", "developer", "architect", "analyst",
                 "scientist", "researcher", "devops", "sre"]


def is_relevant(title: str) -> bool:
    """Return True if this job title warrants inclusion in the review file."""
    t = title.lower()
    if any(k in t for k in RELEVANT_STRONG):
        return True
    if any(k in t for k in EXCLUDED):
        return False
    if any(k in t for k in RELEVANT_WEAK):
        return True
    return any(s in t for s in _TECH_SIGNALS)


# ── Normalisation ─────────────────────────────────────────────────────────────

def make_job_id(company: str, title: str, url: str) -> str:
    raw = f"{company.lower().strip()}|{title.lower().strip()}|{url.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def normalize(raw: dict) -> dict | None:
    company = str(raw.get("company_name", "")).strip()
    title = str(raw.get("role_title", "")).strip()
    if not company or not title:
        return None
    url = str(raw.get("job_url", "")).strip()
    return {
        "job_id": make_job_id(company, title, url),
        "date_found": raw.get("date_found") or datetime.now().strftime("%Y-%m-%d"),
        "company_name": company,
        "role_title": title,
        "role_category": str(raw.get("role_category", "")).strip(),
        "detected_sector": str(raw.get("detected_sector", "")).strip(),
        "location": str(raw.get("location", "")).strip(),
        "work_model": str(raw.get("work_model", "")).strip(),
        "job_url": url,
        "description": str(raw.get("description", "")).strip()[:2000],
        "fit_score": "",
        "fit_summary": "",
        "risks": "",
        "approved_for_cv": "",
        "status": "new",
        "notes": str(raw.get("notes", "")).strip(),
    }


# ── ATS detection ─────────────────────────────────────────────────────────────

def detect_ats(html: str) -> str:
    h = html.lower()
    if "greenhouse.io" in h or "grnh.se" in h:
        return "greenhouse"
    if "jobs.lever.co" in h or "lever.co/embed" in h:
        return "lever"
    if "ashbyhq.com" in h:
        return "ashby"
    if "comeet.com/jobs" in h:
        return "comeet"
    if "myworkdayjobs.com" in h:
        return "workday"
    if "apply.workable.com" in h or "workable.com/widget" in h:
        return "workable"
    if "smartrecruiters.com" in h:
        return "smartrecruiters"
    if "breezy.hr" in h:
        return "breezy"
    if "icims.com" in h:
        return "icims"
    if "jobvite.com" in h:
        return "jobvite"
    return "unknown"


# ── Greenhouse ────────────────────────────────────────────────────────────────

_GH_SLUG_SKIP = frozenset(["embed", "api", "jobs", "board", "job_board", "widget"])
_GH_HEX_RE = re.compile(r'^[0-9a-f]{16,}$')  # reject hex tokens (e.g. embed secrets)


def _gh_slug(html: str) -> str | None:
    for pat in [
        r'greenhouse\.io/embed/job_board\?for=([a-zA-Z0-9_\-]+)',
        r'boards\.greenhouse\.io/([a-zA-Z0-9_\-]+)',
        r'"token"\s*:\s*"([a-zA-Z0-9_\-]+)"',
        r"'token'\s*:\s*'([a-zA-Z0-9_\-]+)'",
    ]:
        m = re.search(pat, html)
        if not m:
            continue
        slug = m.group(1).lower().rstrip("/")
        if slug in _GH_SLUG_SKIP:
            continue
        if _GH_HEX_RE.match(slug):
            continue
        return slug
    return None


def _fetch_greenhouse(company: str, html: str) -> tuple:
    """Returns (jobs, status)."""
    if not REQUESTS_AVAILABLE:
        return [], "source_needs_characterization"
    slug = _gh_slug(html)
    if not slug:
        log.warning(f"  [{company}] Greenhouse: slug not found in HTML")
        return [], "source_needs_characterization"
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
    try:
        time.sleep(ATS_DELAY)
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            log.warning(f"  [{company}] Greenhouse 404 for slug={slug}")
            return [], "no_jobs_found"
        if resp.status_code != 200:
            log.warning(f"  [{company}] Greenhouse HTTP {resp.status_code}")
            return [], "source_needs_characterization"
        raw_list = resp.json().get("jobs", [])
        log.info(f"  [{company}] Greenhouse: {len(raw_list)} total jobs (slug={slug})")
        jobs = []
        for j in raw_list:
            title = j.get("title", "").strip()
            if not title or not is_relevant(title):
                continue
            loc_obj = j.get("location", {}) or {}
            job = normalize({
                "company_name": company,
                "role_title": title,
                "location": loc_obj.get("name", ""),
                "job_url": j.get("absolute_url", ""),
                "notes": f"Greenhouse slug={slug}",
            })
            if job:
                jobs.append(job)
        log.info(f"  [{company}] {len(jobs)} relevant after filter")
        return jobs, ("scan_ok" if jobs else "no_jobs_found")
    except Exception as e:
        log.warning(f"  [{company}] Greenhouse error: {e}")
        return [], "source_needs_characterization"


# ── Lever ─────────────────────────────────────────────────────────────────────

def _lever_slug(html: str) -> str | None:
    for pat in [
        r'jobs\.lever\.co/([a-zA-Z0-9_\-]+)',
        r'lever\.co/([a-zA-Z0-9_\-]+)/embed',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return m.group(1).lower().rstrip("/")
    return None


def _fetch_lever(company: str, html: str) -> tuple:
    if not REQUESTS_AVAILABLE:
        return [], "source_needs_characterization"
    slug = _lever_slug(html)
    if not slug:
        log.warning(f"  [{company}] Lever: slug not found")
        return [], "source_needs_characterization"
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        time.sleep(ATS_DELAY)
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            log.warning(f"  [{company}] Lever HTTP {resp.status_code}")
            return [], "source_needs_characterization"
        raw_list = resp.json()
        if not isinstance(raw_list, list):
            return [], "no_jobs_found"
        log.info(f"  [{company}] Lever: {len(raw_list)} total jobs (slug={slug})")
        jobs = []
        for j in raw_list:
            title = j.get("text", "").strip()
            if not title or not is_relevant(title):
                continue
            cats = j.get("categories", {}) or {}
            location = cats.get("location", "") or cats.get("allLocations", "") or ""
            if isinstance(location, list):
                location = "; ".join(location)
            job = normalize({
                "company_name": company,
                "role_title": title,
                "location": str(location).strip(),
                "job_url": j.get("hostedUrl", ""),
                "notes": f"Lever slug={slug}",
            })
            if job:
                jobs.append(job)
        log.info(f"  [{company}] {len(jobs)} relevant after filter")
        return jobs, ("scan_ok" if jobs else "no_jobs_found")
    except Exception as e:
        log.warning(f"  [{company}] Lever error: {e}")
        return [], "source_needs_characterization"


# ── Ashby ─────────────────────────────────────────────────────────────────────

def _ashby_slug(html: str) -> str | None:
    _skip = {"embed", "apply", "careers", "jobs"}
    for pat in [
        r'jobs\.ashbyhq\.com/([a-zA-Z0-9_\-]+)',
        r'ashbyhq\.com/([a-zA-Z0-9_\-]+)',
    ]:
        for m in re.finditer(pat, html, re.IGNORECASE):
            s = m.group(1).lower().rstrip("/")
            if s not in _skip:
                return s
    return None


def _fetch_ashby(company: str, html: str) -> tuple:
    if not REQUESTS_AVAILABLE:
        return [], "source_needs_characterization"
    slug = _ashby_slug(html)
    if not slug:
        log.warning(f"  [{company}] Ashby: slug not found")
        return [], "source_needs_characterization"
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        time.sleep(ATS_DELAY)
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            log.warning(f"  [{company}] Ashby HTTP {resp.status_code}")
            return [], "source_needs_characterization"
        raw_list = resp.json().get("jobPostings", [])
        log.info(f"  [{company}] Ashby: {len(raw_list)} total jobs (slug={slug})")
        jobs = []
        for j in raw_list:
            title = j.get("title", "").strip()
            if not title or not is_relevant(title):
                continue
            location = j.get("locationName", "") or j.get("location", "") or ""
            job_url = j.get("jobUrl", "") or f"https://jobs.ashbyhq.com/{slug}/{j.get('id','')}"
            job = normalize({
                "company_name": company,
                "role_title": title,
                "location": str(location).strip(),
                "job_url": job_url,
                "notes": f"Ashby slug={slug}",
            })
            if job:
                jobs.append(job)
        log.info(f"  [{company}] {len(jobs)} relevant after filter")
        return jobs, ("scan_ok" if jobs else "no_jobs_found")
    except Exception as e:
        log.warning(f"  [{company}] Ashby error: {e}")
        return [], "source_needs_characterization"


# ── Comeet ────────────────────────────────────────────────────────────────────

# Matches url_comeet_hosted_page JSON fields embedded in career page HTML
_COMEET_EMBED_PAT = re.compile(
    r'url_comeet_hosted_page.{1,20}'
    r'(https?://(?:www\.)?comeet\.com/jobs/'
    r'[a-zA-Z0-9_\-]+/[0-9.]+/([a-zA-Z0-9_\-]+)/[A-Z0-9.]+)',
    re.IGNORECASE,
)


def _comeet_board_url(html: str) -> str | None:
    """Extract the Comeet company board root URL (not a specific job listing)."""
    m = re.search(r'comeet\.com/jobs/([a-zA-Z0-9_\-]+)/([0-9.]+)', html, re.IGNORECASE)
    if m:
        return f"https://www.comeet.com/jobs/{m.group(1)}/{m.group(2)}"
    return None


def _comeet_jobs_from_html(company: str, html: str) -> list:
    """Extract Comeet job listings from JSON data embedded in the careers page."""
    jobs = []
    seen_slugs: set = set()
    for m in _COMEET_EMBED_PAT.finditer(html):
        full_url = m.group(1)
        job_slug = m.group(2)
        if job_slug in seen_slugs:
            continue
        seen_slugs.add(job_slug)
        title = job_slug.replace("-", " ").title()
        if not is_relevant(title):
            continue
        job = normalize({
            "company_name": company,
            "role_title": title,
            "job_url": full_url,
            "notes": "Comeet (embedded)",
        })
        if job:
            jobs.append(job)
    return jobs


def _fetch_comeet(company: str, html: str) -> tuple:
    if not BS4_AVAILABLE:
        return [], "source_needs_characterization"

    # Strategy 1: extract from JSON data already embedded in the careers page
    embedded = _comeet_jobs_from_html(company, html)
    if embedded:
        log.info(f"  [{company}] Comeet: {len(embedded)} relevant jobs (embedded data)")
        return embedded, "scan_ok"

    # Strategy 2: fetch the Comeet board page and parse HTML links
    if not REQUESTS_AVAILABLE:
        return [], "source_needs_characterization"
    board_url = _comeet_board_url(html)
    if not board_url:
        log.warning(f"  [{company}] Comeet: board URL not found")
        return [], "source_needs_characterization"
    try:
        time.sleep(ATS_DELAY)
        resp = requests.get(board_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code >= 400:
            log.warning(f"  [{company}] Comeet HTTP {resp.status_code}")
            return [], "source_needs_characterization"
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        seen: set = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if not text or len(text) < 4 or len(text) > 120:
                continue
            if "comeet.com/jobs" not in href and "/jobs/" not in href:
                continue
            if not is_relevant(text):
                continue
            norm = text.lower().strip()
            if norm in seen:
                continue
            seen.add(norm)
            full_url = href if href.startswith("http") else f"https://www.comeet.com{href}"
            job = normalize({
                "company_name": company,
                "role_title": text,
                "job_url": full_url,
                "notes": "Comeet",
            })
            if job:
                jobs.append(job)
        log.info(f"  [{company}] Comeet: {len(jobs)} relevant jobs from {board_url}")
        return jobs, ("scan_ok" if jobs else "no_jobs_found")
    except Exception as e:
        log.warning(f"  [{company}] Comeet error: {e}")
        return [], "source_needs_characterization"


# ── Generic HTML fallback ─────────────────────────────────────────────────────

_JOB_URL_PAT = re.compile(
    r'/jobs?/|/careers?/|/positions?/|/openings?/|/roles?/|/vacancies?/'
    r'|greenhouse\.io|lever\.co|ashbyhq|comeet|workday|jobvite|icims',
    re.IGNORECASE,
)

_SKIP_TEXTS = frozenset([
    "careers", "jobs", "apply", "apply now", "view all", "see all",
    "learn more", "open positions", "view openings", "join us",
    "current openings", "all jobs", "all positions",
])


def _parse_generic(company: str, soup) -> tuple:
    jobs = []
    seen_titles: set = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        text = a.get_text(separator=" ", strip=True)
        if not text or len(text) < 5 or len(text) > 100:
            continue
        if text.lower() in _SKIP_TEXTS:
            continue
        if not _JOB_URL_PAT.search(href):
            continue
        if not is_relevant(text):
            continue
        norm = re.sub(r"\s+", " ", text).lower().strip()
        if norm in seen_titles:
            continue
        seen_titles.add(norm)
        # Resolve relative URLs (best-effort)
        if href.startswith("//"):
            href = "https:" + href
        job = normalize({
            "company_name": company,
            "role_title": text,
            "job_url": href,
            "notes": "generic HTML scrape",
        })
        if job:
            jobs.append(job)
    return jobs, ("scan_ok" if jobs else "no_jobs_found")


# ── Per-company HTML dispatch ─────────────────────────────────────────────────

_run_stats: dict = {}   # populated during run(); cleared at start of each run()
_run_ats: dict = {}     # ATS type detected per company; cleared at start of each run()


def parse_html_for_company(company_name: str, html_file: Path) -> tuple:
    """Dispatch to appropriate parser. Returns (jobs, status)."""
    if not BS4_AVAILABLE:
        return [], "source_needs_characterization"
    try:
        html = html_file.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        log.warning(f"  [{company_name}] Cannot read HTML: {e}")
        return [], "parse_error"

    if len(html) < 300:
        log.info(f"  [{company_name}] HTML too short — likely a redirect or empty response")
        return [], "no_jobs_found"

    ats = detect_ats(html)
    _run_ats[company_name] = ats
    log.info(f"  [{company_name}] ATS={ats}")

    if ats == "greenhouse":
        return _fetch_greenhouse(company_name, html)
    if ats == "lever":
        return _fetch_lever(company_name, html)
    if ats == "ashby":
        return _fetch_ashby(company_name, html)
    if ats == "comeet":
        return _fetch_comeet(company_name, html)
    if ats in ("workday", "workable", "smartrecruiters", "breezy", "icims", "jobvite"):
        log.info(f"  [{company_name}] {ats.title()} requires JS/special handling → source_needs_characterization")
        return [], "source_needs_characterization"

    # Unknown ATS — try generic HTML
    soup = BeautifulSoup(html, "html.parser")
    return _parse_generic(company_name, soup)


def _load_company_slug_map() -> dict:
    """slug → canonical company name from target_companies.csv."""
    companies_csv = BASE_DIR / "config" / "target_companies.csv"
    mapping = {}
    try:
        with open(companies_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row["company_name"].strip()
                slug = name.lower().replace(" ", "_").replace("/", "_")
                mapping[slug] = name
    except Exception:
        pass
    return mapping


def parse_all_raw_html() -> list:
    """Walk data/raw/<company>/ dirs, parse latest HTML per company."""
    global _run_stats
    jobs = []
    if not RAW_DIR.exists():
        return jobs

    slug_map = _load_company_slug_map()

    for company_dir in sorted(RAW_DIR.iterdir()):
        if not company_dir.is_dir() or company_dir.name == "manual":
            continue
        slug = company_dir.name
        company_name = slug_map.get(slug) or slug.replace("_", " ").title()

        html_files = sorted(company_dir.glob("*.html"))
        if not html_files:
            _run_stats[company_name] = "no_html_file"
            continue

        html_file = html_files[-1]  # most recent date
        company_jobs, status = parse_html_for_company(company_name, html_file)
        _run_stats[company_name] = status
        jobs.extend(company_jobs)
        log.info(f"[{company_name}] status={status}  jobs_found={len(company_jobs)}")

    return jobs


def get_run_stats() -> dict:
    """Return per-company characterisation from the most recent run().

    Returns: {company_name: {"status": str, "ats": str}}
      status: scan_ok | no_jobs_found | source_needs_characterization | parse_error | no_html_file
      ats:    greenhouse | lever | ashby | comeet | workday | workable | ... | unknown
    """
    merged = {}
    for name, status in _run_stats.items():
        merged[name] = {
            "status": status,
            "ats": _run_ats.get(name, "unknown"),
        }
    return merged


# ── Manual JSON entries ───────────────────────────────────────────────────────

def parse_manual_jobs() -> list:
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    for fpath in sorted(MANUAL_DIR.glob("*.json")):
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"Could not read {fpath.name}: {e}")
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            job = normalize(item)
            if job:
                jobs.append(job)
                log.info(f"  manual: {job['company_name']} — {job['role_title']}")
            else:
                log.warning(f"  skipped invalid record in {fpath.name}")
    return jobs


# ── Save parsed output ────────────────────────────────────────────────────────

def save_parsed(jobs: list) -> Path:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    out = PARSED_DIR / f"{date_str}_parsed_jobs.json"
    out.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Saved {len(jobs)} parsed jobs → {out.relative_to(BASE_DIR)}")
    return out


# ── Main entry point ──────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> list:
    global _run_stats, _run_ats
    _run_stats = {}
    _run_ats = {}

    all_jobs = []
    all_jobs.extend(parse_manual_jobs())
    all_jobs.extend(parse_all_raw_html())

    # Deduplicate by job_id (keep first occurrence)
    seen_ids: set = set()
    unique = []
    for job in all_jobs:
        if job["job_id"] not in seen_ids:
            seen_ids.add(job["job_id"])
            unique.append(job)

    log.info(f"Parsed {len(all_jobs)} total, {len(unique)} unique jobs")

    if not dry_run:
        save_parsed(unique)

    return unique


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse fetched career data")
    parser.add_argument("--dry-run", action="store_true", help="Parse without saving output")
    args = parser.parse_args()
    jobs = run(dry_run=args.dry_run)
    log.info(f"Done — {len(jobs)} jobs")
