# Chore Bot

A Telegram bot for you and your wife to log chores in a group chat.

## How It Works

1. You or your wife type a message in the group chat — "washed the dishes"
2. The bot logs it and replies with ✅
3. Use `/chores` to see your recent chores
4. Use `/clear` to clear your chore list

## Setup

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 2. Create a Group Chat

1. Create a group in Telegram with you, your wife, and the bot
2. Make the bot an admin if you want it to see all messages

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your `BOT_TOKEN`.

### 4. Run

**With Docker:**

```bash
docker-compose up -d
```

**Without Docker:**

```bash
pip install -r requirements.txt
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Get help |
| `/chore <text>` | Log a chore |
| `/chores` | See your recent chores |
| `/clear` | Clear your chores |
| `/admin` | Show bot stats (admin only) |
| `/ban <user_id>` | Ban a user (admin only) |
| `/unban <user_id>` | Unban a user (admin only) |

## Daily Summary

At 5 AM Manila time, the bot sends a daily chore summary to the group chat.
Set `REPORT_CHAT_ID` in your `.env` to the chat ID of the group chat.

The last report time is persisted in the database, so bot restarts won't cause
any chores to be missed.

You can also just type any message and it will be logged automatically.

## Deployment

This project runs on a **greencloud VPS** under `/opt/chore-bot/` using Docker.

### Deploying updates

```bash
git push greencloud main
ssh root@greencloud
cd /opt/chore-bot
git pull origin main
docker compose up -d --build
```
