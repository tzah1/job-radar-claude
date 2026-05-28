# Scoring Rules — Job Radar v1

## Score Range
1–10 (integer). Implemented in scripts/score_jobs.py using keyword matching (no LLM in v1).

## Scoring Dimensions

### 1. Role Fit (up to +2.5)
- **+2.5**: Title or description directly matches: data engineer, analytics engineer, data pipeline,
  AI ops, mlops, data ops, big data, etl/elt, data platform, data infrastructure
- **+1.0**: Moderate match: data analyst (engineering-adjacent), BI engineer, platform engineer,
  python developer (data context), AI/ML engineer
- **-2.0**: Mismatch signals: frontend developer, mobile developer, research scientist,
  pure UI/UX, theoretical ML, PhD research

### 2. Sector Fit (up to +1.0)
- **+1.0**: Cyber, cybersecurity, security, AI, machine learning, fintech, data, big data
- **+0.5**: Cloud, SaaS, healthtech, insurtech

### 3. Location and Work Model Fit (up to +0.5, down to -1.0)
- **+0.5**: Location in preferred range (Tel Aviv, Herzliya, Petah Tikva, Ramat Gan, Givatayim)
  OR work model is hybrid/remote/flexible
- **-0.5**: Fully onsite signals detected
- **-1.0**: Location outside range (Haifa, Beer Sheva, Jerusalem, Eilat) AND no remote option

### 4. Work-Life Balance / Parent-Friendly (up to +0.5)
- **+0.5**: Keywords: flexible hours, parent-friendly, family-friendly, work-life balance,
  remote-first, async, flexible work

### 5. CV Alignment (up to +1.0)
- **+1.0**: 3+ CV skill keywords present: splunk, python, sql, bash, data quality,
  data validation, normalization, monitoring, data pipeline, etl, analytics workflow
- **+0.5**: 1–2 CV skill keywords present

## Score Interpretation
| Score | Meaning |
|-------|---------|
| 8–10  | Strong fit — prioritize review |
| 6–7   | Good fit — review with moderate urgency |
| 4–5   | Partial fit — review when time allows |
| 2–3   | Weak fit — low priority |
| 1     | Poor fit — consider rejecting |

## Important
- Score is a signal, not a gate. Final approval is always manual.
- v1 uses keyword matching only. Claude analysis may be added in a future step for approved jobs.
- Never auto-reject based on score alone. Always surface to review file.

## TODO (future improvement)
- Add company-specific score bonuses (e.g., referral angle, known great culture)
- Claude-assisted re-scoring for jobs with score 6–7 that need deeper analysis
