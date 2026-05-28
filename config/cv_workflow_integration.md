# CV Workflow Integration

## Overview
Job Radar prepares structured input packages for the existing CV-tailoring workflow.
It does NOT tailor CVs itself.

## What Job Radar Provides
When a job is approved (`approved_for_cv=yes`) and `prepare_approved_jobs.py` is run,
a folder is created at:

```
data/approved_jobs/<company>_<role>_<date>/
├── job-description.md      # Full job description text
├── fit-analysis.md         # Scored fit breakdown, gaps, risks
├── cv-tailoring-input.md   # Structured briefing for the CV workflow
└── metadata.json           # Machine-readable metadata
```

## cv-tailoring-input.md Contents
Each cv-tailoring-input.md includes:
- Company name and background
- Role title and URL
- Location and work model
- Full job description (if available)
- Fit summary and score
- Identified risks and gaps
- Keywords to reflect in the CV
- Hard constraints:
  - Do not invent or embellish experience
  - Use existing master CV as the source of truth
  - Maintain positioning as Data Engineer / Analytics Engineer / AI-enabled workflows

## Calling the CV Workflow

### TODO: Replace the placeholder below with the actual command once confirmed
The CV workflow command should be called from `scripts/prepare_approved_jobs.py`
after the job folder is created. The current script includes a clear TODO marker
at the integration point.

Expected call pattern (placeholder — do not use until confirmed):
```
# TODO: replace with actual CV workflow command
# Example: python ~/cv-workflow/tailor_cv.py --input data/approved_jobs/<folder>/
# Or:      claude-code "tailor CV for role at <company>"  --context <folder>/cv-tailoring-input.md
```

### When to Call It
- Only after folder creation succeeds
- Only for rows where `approved_for_cv=yes`
- Only when you have reviewed fit-analysis.md and agree with the assessment

## What Remains Manual
- Final CV review and edits
- Submitting the application
- Writing mentor messages (always 100% manual — never automated)
- Deciding which version of the CV to submit

## Mentor Messages
No mentor message preparation is part of this workflow.
All mentor outreach is written manually, based on your personal judgment.
