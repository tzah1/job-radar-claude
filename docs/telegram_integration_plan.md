# Telegram Integration Plan

**Status**: Not implemented in v1. This document records the future plan.

---

## Purpose
Allow daily job radar notifications and lightweight approval via Telegram,
without changing the core local CSV workflow.

---

## Phase 1 — Notifications (read-only)

**Trigger**: After `run_daily_scan.py` completes  
**Action**: Send `exports/daily_summary.md` content as a Telegram message  
**Bot**: Personal bot, single chat ID

Implementation:
1. Create a Telegram bot via @BotFather
2. Get `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
3. Store both in `.env` (never in git)
4. Add `scripts/notify_telegram.py` with a simple `send_message(text)` function
5. Call from `run_daily_scan.py` at the end (optional, gated by env var)

```python
# Pseudocode for notify_telegram.py
import os, requests
def send_daily_summary(summary_text: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return  # silently skip if not configured
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": summary_text[:4096], "parse_mode": "Markdown"}
    )
```

---

## Phase 2 — Approval from Telegram (informational only)

**Concept**: Send a list of new jobs with their `job_id`s.  
Reply with a job_id to mark it as `approved_for_cv=yes` in the CSV.

**Important constraints**:
- This only writes `approved_for_cv=yes` to the CSV
- It does NOT trigger CV tailoring automatically
- You still run `prepare_approved_jobs.py` manually after
- No applications are ever sent from Telegram

Implementation sketch:
1. Add a long-polling or webhook listener in `scripts/telegram_bot.py`
2. Commands to support:
   - `/jobs` — list today's new jobs
   - `/approve <job_id>` — mark approved in CSV
   - `/reject <job_id>` — mark rejected
   - `/summary` — resend today's summary
3. On each command, read/write the local CSV directly
4. Add `telegram_bot.py` as a background process (optional, separate from daily scan)

---

## What Telegram Will NEVER Do

- Send job applications
- Contact recruiters or mentors
- Trigger CV tailoring automatically
- Access external services beyond the Telegram API
- Approve bulk jobs without explicit per-job confirmation

---

## Security Considerations

- Bot token goes in `.env`, never in git
- `TELEGRAM_CHAT_ID` restricts the bot to your personal chat only
- Validate all incoming messages are from your `TELEGRAM_CHAT_ID` before acting
- Log all commands received to `logs/telegram_bot.log`

---

## Dependencies to Add (when implementing)

No new packages needed for Phase 1 — `requests` already in requirements.txt.

For Phase 2 (polling/webhook), optionally:
- `python-telegram-bot` — well-maintained, widely used
- Or implement manually with `requests` + long polling (simpler, no extra dep)
