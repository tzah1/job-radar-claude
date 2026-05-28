#!/usr/bin/env python3
"""
score_jobs.py - Score job records using keyword-based rules (no LLM required)

Scoring dimensions (see config/scoring_rules.md for full breakdown):
  1. Role fit        — title/description keyword match
  2. Sector fit      — industry/domain signals
  3. Location fit    — city names and work model
  4. Balance signals — parent-friendly / flexibility mentions
  5. CV alignment    — known skills from profile_context.md

Returns score 1–10, fit_summary string, risks string.

Usage:
    python scripts/score_jobs.py --input data/parsed/YYYYMMDD_parsed_jobs.json
    Also importable: score_job(job_dict) -> (score, fit_summary, risks)
"""

import json
import logging
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LOG_FILE = BASE_DIR / "logs" / "daily_scan.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ── Role fit ────────────────────────────────────────────────────────────────
ROLE_HIGH = [
    "data engineer", "analytics engineer", "data engineering", "analytics engineering",
    "data platform", "data infrastructure", "data pipeline", "data pipelines",
    "ai engineer", "ml engineer", "ai ops", "mlops", "aiops",
    "data ops", "dataops", "data operations",
    "big data", "etl", "elt", "dbt", "airflow", "spark", "kafka",
]
ROLE_MEDIUM = [
    "data analyst", "analytics", "business intelligence", "bi engineer",
    "data architect", "data warehouse", "lakehouse", "snowflake", "databricks",
    "python developer", "backend engineer", "platform engineer",
    "security data", "siem", "log analysis", "log analytics",
]
ROLE_LOW = [
    "data scientist", "data manager", "data governance", "data quality manager",
    "soc analyst", "security analyst", "cyber analyst",
]
ROLE_NEGATIVE = [
    "frontend developer", "frontend engineer", "ui developer", "react developer",
    "angular developer", "vue developer", "mobile developer", "ios developer",
    "android developer", "research scientist", "phd researcher",
    "theoretical", "pure research",
]

# ── Sector fit ───────────────────────────────────────────────────────────────
SECTOR_HIGH = [
    "cyber", "cybersecurity", "cybersec", "security", "infosec", "devsecops",
    "siem", "threat detection", "threat intelligence",
    "artificial intelligence", "machine learning",
    "data", "big data", "analytics platform",
    "fintech", "financial technology", "payments",
]
SECTOR_MEDIUM = [
    "cloud", "saas", "platform", "infrastructure", "devops",
    "health tech", "healthtech", "insurtech", "insurance technology",
]

# ── Location ─────────────────────────────────────────────────────────────────
LOCATION_GOOD = [
    "tel aviv", "herzliya", "petah tikva", "petah tiqva",
    "ramat gan", "givatayim", "bnei brak", "holon", "bat yam",
]
LOCATION_ACCEPTABLE = [
    "modiin", "modi'in", "rehovot", "rishon lezion", "rishon le-zion",
    "yavne",
]
LOCATION_BAD = ["haifa", "beer sheva", "be'er sheva", "jerusalem", "eilat", "nazareth"]

WORK_MODEL_GOOD = ["hybrid", "remote", "flexible", "remote-first", "work from home", "wfh"]
WORK_MODEL_BAD = [
    "on-site only", "onsite only", "fully onsite", "office only", "in-office only",
    "100% office", "no remote",
]

# ── Balance ───────────────────────────────────────────────────────────────────
BALANCE_POSITIVE = [
    "flexible hours", "parent", "parental", "family", "family-friendly",
    "work-life balance", "work life balance", "remote-first", "async",
    "flexible work", "school hours",
]

# ── CV skills ─────────────────────────────────────────────────────────────────
CV_SKILLS = [
    "splunk", "python", "sql", "bash", "shell scripting",
    "data quality", "data validation", "normalization", "monitoring",
    "data pipeline", "data pipelines", "etl", "analytics workflow",
    "data engineering", "analytics engineering",
    "dbt", "airflow", "spark", "kafka", "snowflake",
]


def _matches(text: str, keywords: list) -> list:
    t = text.lower()
    return [kw for kw in keywords if kw in t]


def classify_role_category(title: str, description: str) -> str:
    combined = f"{title} {description}".lower()
    if any(k in combined for k in ["data engineer", "data engineering", "data pipeline", "etl", "elt"]):
        return "Data Engineering"
    if any(k in combined for k in ["analytics engineer", "analytics engineering", "dbt"]):
        return "Analytics Engineering"
    if any(k in combined for k in ["ai ops", "mlops", "aiops", "ai engineer", "ml engineer"]):
        return "AI/ML Engineering"
    if any(k in combined for k in ["data ops", "dataops", "data operations"]):
        return "Data Operations"
    if any(k in combined for k in ["big data", "data platform", "data infrastructure"]):
        return "Data Platform"
    if any(k in combined for k in ["data analyst", "analytics", "business intelligence", "bi "]):
        return "Analytics"
    if any(k in combined for k in ["cyber", "security", "infosec", "soc", "siem"]):
        return "Cyber/Security"
    if any(k in combined for k in ["machine learning", "nlp", "deep learning"]):
        return "AI/ML"
    return "Other"


def detect_sector(notes: str, description: str) -> str:
    combined = f"{notes} {description}".lower()
    if any(k in combined for k in ["cyber", "cybersecurity", "security", "infosec", "siem"]):
        return "Cyber/Security"
    if any(k in combined for k in ["fintech", "financial", "payment", "banking", "insurance"]):
        return "Fintech"
    if any(k in combined for k in ["health", "medical", "clinical", "therapy", "pharma"]):
        return "HealthTech"
    if any(k in combined for k in ["ai", "artificial intelligence", "machine learning"]):
        return "AI"
    if any(k in combined for k in ["data", "analytics", "big data"]):
        return "Data"
    return "SaaS/Tech"


def score_job(job: dict) -> tuple:
    """
    Score a single job record.
    Returns (score: int, fit_summary: str, risks: str).
    Also fills role_category and detected_sector in-place if blank.
    """
    title = job.get("role_title", "")
    desc = job.get("description", "")
    location = job.get("location", "")
    work_model = job.get("work_model", "")
    notes = job.get("notes", "")
    combined = f"{title} {desc} {notes}"

    score = 5.0
    positives = []
    negatives = []

    # 1. Role fit
    high_hits = _matches(combined, ROLE_HIGH)
    med_hits = _matches(combined, ROLE_MEDIUM)
    neg_hits = _matches(combined, ROLE_NEGATIVE)
    if high_hits:
        score += 2.5
        positives.append(f"Strong role fit: {', '.join(high_hits[:3])}")
    elif med_hits:
        score += 1.0
        positives.append(f"Moderate role fit: {', '.join(med_hits[:3])}")
    if neg_hits:
        score -= 2.0
        negatives.append(f"Role mismatch: {', '.join(neg_hits[:2])}")

    # 2. Sector fit
    sec_high = _matches(combined, SECTOR_HIGH)
    sec_med = _matches(combined, SECTOR_MEDIUM)
    if sec_high:
        score += 1.0
        positives.append(f"Good sector: {', '.join(sec_high[:2])}")
    elif sec_med:
        score += 0.5

    # 3. Location fit
    loc_text = f"{location} {work_model}"
    loc_good = _matches(loc_text.lower(), LOCATION_GOOD)
    loc_bad = _matches(loc_text.lower(), LOCATION_BAD)
    wm_good = _matches(loc_text.lower() + " " + combined.lower(), WORK_MODEL_GOOD)
    wm_bad = _matches(combined.lower(), WORK_MODEL_BAD)

    if loc_good or wm_good:
        score += 0.5
        positives.append("Good location/hybrid model")
    if loc_bad and not wm_good:
        score -= 1.0
        negatives.append(f"Location outside preferred range: {location}")
    if wm_bad:
        score -= 0.5
        negatives.append("Fully onsite signals")

    # 4. Work-life balance
    balance_hits = _matches(combined, BALANCE_POSITIVE)
    if balance_hits:
        score += 0.5
        positives.append("Flexible / parent-friendly signals")

    # 5. CV alignment
    cv_hits = _matches(combined, CV_SKILLS)
    if len(cv_hits) >= 3:
        score += 1.0
        positives.append(f"Strong CV alignment: {', '.join(cv_hits[:4])}")
    elif cv_hits:
        score += 0.5
        positives.append(f"Partial CV alignment: {', '.join(cv_hits[:2])}")

    score = max(1, min(10, round(score)))

    # Auto-classify if empty
    if not job.get("role_category"):
        job["role_category"] = classify_role_category(title, desc)
    if not job.get("detected_sector"):
        job["detected_sector"] = detect_sector(notes, desc)

    fit_summary = "; ".join(positives) if positives else "No strong match signals"
    risks = "; ".join(negatives) if negatives else ""

    return score, fit_summary, risks


def run(jobs: list, dry_run: bool = False) -> list:
    for job in jobs:
        score, summary, risks = score_job(job)
        job["fit_score"] = score
        job["fit_summary"] = summary
        job["risks"] = risks
        log.info(f"  scored [{score}/10] {job.get('company_name','')} — {job.get('role_title','')}")
    return jobs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score parsed jobs")
    parser.add_argument("--input", required=True, help="Path to parsed jobs JSON")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    jobs = json.loads(Path(args.input).read_text(encoding="utf-8"))
    scored = run(jobs, dry_run=args.dry_run)
    print(json.dumps(scored, indent=2, ensure_ascii=False))
