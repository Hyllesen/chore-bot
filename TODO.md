# TODO

## Goal
Build a Python Telegram bot that lets you and your wife log chores in a group chat, stored in SQLite and deployed as a Docker container.

## Tasks

### 1. Project Setup
- [x] Create `requirements.txt` with dependencies (python-telegram-bot, aiosqlite)
- [x] Create `.env.example` with `BOT_TOKEN` and `ADMIN_CHAT_ID` placeholders
- [x] Create `Dockerfile` with a slim Python base image

### 2. Database Layer
- [x] Create `database.py` with async SQLite initialization (tables: `chores` with id, user_id, username, chore_text, timestamp)
- [x] Implement `add_chore(user_id, username, chore_text)` function
- [x] Implement `get_chores(user_id)` function (recent chores, maybe last 20)
- [x] Implement `clear_chores(user_id)` function

### 3. Bot Core
- [x] Create `bot.py` with the main bot entry point using `python-telegram-bot` (async)
- [x] Add command handler for `/start` — greet user and explain how to use the bot
- [x] Add command handler for `/chore` — accept text after the command as a chore entry (e.g., `/chore washed the dishes`)
- [x] Add command handler for `/chores` — list recent chores for the user
- [x] Add command handler for `/clear` — clear all chores for the user
- [x] Add message handler — if user just sends text (no command), treat it as a chore entry automatically
- [x] Add inline button support for `/chores` listing so users can quick-add common chores (e.g., dishes, laundry, vacuuming)

### 4. Admin Controls
- [x] Add `/admin` command to show bot stats (total chores logged, active users)
- [x] Add `/ban` command to block a user from using the bot
- [x] Add `/unban` command to unblock a user

### 5. Docker & Deployment
- [x] Create `docker-compose.yml` with the bot service and a volume for SQLite data
- [x] Create `Dockerfile` with multi-stage build (slim image)
- [x] Test the container builds and runs locally

### 6. Testing
- [x] Write unit tests for database layer (add, retrieve, clear chores)
- [x] Write integration tests for bot commands using python-telegram-bot's test utilities
- [x] Test the Docker container end-to-end with a test token

## Notes
- Use `aiosqlite` for async SQLite access (works with python-telegram-bot's async handlers)
- The `ADMIN_CHAT_ID` env var restricts admin commands to a specific chat
- The bot should handle both commands (`/chore laundry`) and plain messages ("I did the laundry") as chore entries
- SQLite file stored in `/data/chores.db` inside the container, mapped via Docker volume
