# TODO

## Goal
Add a daily 5 AM (Manila time) summary message to the group chat showing who did what chores that day.

## Tasks

### 1. Dependencies & Configuration
- [x] Add `pytz` to `requirements.txt` for timezone handling
- [x] Add `REPORT_CHAT_ID` to `.env.example` (and update README with the new env var)

### 2. Database Layer
- [x] Add `get_chores_since(timestamp)` function in `database.py` that returns all chores created after a given timestamp (includes user_id, username, chore_text, created_at)

### 3. Bot — Daily Report Logic
- [x] Add a `send_daily_report` function in `bot.py` that queries chores since last run, groups by user, and formats a summary message like "📋 Daily Chore Summary\n\n👤 Stefan: washed dishes, vacuumed\n👤 Jane: cooked dinner\n\nTotal: 3 chores by 2 people"
- [x] Add a `daily_report_job` callback using `ContextTypes.DEFAULT_TYPE` that calls `send_daily_report` via `context.bot.send_message(REPORT_CHAT_ID, ...)`
- [x] Schedule the job to run at 5 AM Asia/Manila time using `context.job_queue.run_daily(daily_report_job, time=5am_manila, name="daily_report")` inside `post_init`

### 4. Testing
- [x] Write a unit test for `get_chores_since()` — verify it returns only chores after a given timestamp
- [x] Write a unit test for the daily report formatting — verify user grouping and message structure

## Notes
- 5 AM Manila = 05:00 Asia/Manila (UTC+8) = 21:00 UTC previous day
- The job uses `context.job_queue.run_daily()` from python-telegram-bot's JobQueue
- Track "last run" time as a module-level variable initialized to "now" on bot start (so the first report only covers chores since the bot started)
- If REPORT_CHAT_ID is not set, skip sending the report (log a warning)
- SQLite's `CURRENT_TIMESTAMP` is UTC, so all timestamp comparisons must use UTC
