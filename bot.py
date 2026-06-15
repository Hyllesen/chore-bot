import os
import sys
import logging
from datetime import datetime, timedelta
from collections import defaultdict

import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.background import BackgroundScheduler

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    JobQueue,
)

import database

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
REPORT_CHAT_ID = os.environ.get("REPORT_CHAT_ID")

MANILA_TZ = pytz.timezone("Asia/Manila")

# Track the last time the daily report was sent
# Initialized in post_init from database; falls back to now on first run
last_report_time: datetime | None = None

QUICK_CHORES = [
    ("🍽️ Dishes", "washed dishes"),
    ("🧺 Laundry", "did laundry"),
    ("🧹 Vacuum", "vacuumed"),
    ("🚿 Clean bathroom", "cleaned bathroom"),
    ("🗑️ Take out trash", "took out trash"),
    ("🍳 Cooked dinner", "cooked dinner"),
    ("🧽 Cleaned kitchen", "cleaned kitchen"),
    ("🌿 Watered plants", "watered plants"),
]

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

async def check_banned(user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return True if user is allowed (not banned), False if banned."""
    if await database.is_banned(user_id):
        if update.message:
            await update.message.reply_text("You've been banned from using this bot.")
        elif update.callback_query:
            await update.callback_query.answer("You've been banned from using this bot.", show_alert=True)
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greet the user and explain how to use the bot."""
    user = update.effective_user
    name = user.first_name or "there"

    if not await check_banned(user.id, update, context):
        return

    text = (
        f"Hi {name}! 👋\n\n"
        f"I'll keep track of the chores you do.\n\n"
        f"**How to use me:**\n"
        f"• Just send a message like *I did the dishes* — I'll log it\n"
        f"• Or use */chore <what you did>*\n"
        f"• */chores* — see your recent chores\n"
        f"• */clear* — clear your chore list\n\n"
        f"Start typing and I'll take it from there!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def chore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log a chore from /chore command."""
    user = update.effective_user

    if not await check_banned(user.id, update, context):
        return

    if not context.args:
        await update.message.reply_text("What did you do? Use `/chore <what you did>`")
        return

    chore_text = " ".join(context.args)
    await database.add_chore(user.id, user.username or user.first_name, chore_text)
    await update.message.reply_text("✅ Logged")

async def chores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List recent chores for the user."""
    user = update.effective_user

    if not await check_banned(user.id, update, context):
        return

    user_chores = await database.get_chores(user.id)

    if not user_chores:
        await update.message.reply_text("No chores logged yet. Start doing stuff and tell me!")
        return

    lines = [f"{i+1}. {c['chore_text']} — *{c['created_at']}*" for i, c in enumerate(user_chores)]
    text = f"**Your recent chores:**\n\n" + "\n".join(lines)

    keyboard = [
        [
            InlineKeyboardButton(text=btn_label, callback_data=f"quick_{chore}")
            for btn_label, chore in QUICK_CHORES
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def clear_chores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all chores for the user."""
    user = update.effective_user

    if not await check_banned(user.id, update, context):
        return

    count = await database.clear_chores(user.id)
    if count:
        await update.message.reply_text(f"🗑️ Cleared {count} chore(s).")
    else:
        await update.message.reply_text("Nothing to clear.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Treat any plain text message as a chore entry."""
    user = update.effective_user

    if not await check_banned(user.id, update, context):
        return

    text = update.message.text.strip()
    await database.add_chore(user.id, user.username or user.first_name, text)
    await update.message.reply_text("✅ Logged")

async def handle_quick_chore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks for quick chore logging."""
    query = update.callback_query
    user = query.from_user

    if not await check_banned(user.id, update, context):
        return

    data = query.data
    if not data.startswith("quick_"):
        await query.answer()
        return

    chore_text = data.replace("quick_", "")
    await database.add_chore(user.id, user.username or user.first_name, chore_text)

    await query.answer("✅ Logged")
    await query.edit_message_text("✅ Logged")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot stats (admin only)."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Not authorized.")
        return

    stats = await database.get_stats()
    text = (
        f"**Bot Stats**\n\n"
        f"Total chores logged: {stats['total_chores']}\n"
        f"Active users: {stats['active_users']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user (admin only)."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return

    try:
        user_id = int(context.args[0])
        await database.ban_user(user_id)
        await update.message.reply_text(f"User {user_id} has been banned.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a user (admin only)."""
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return

    try:
        user_id = int(context.args[0])
        await database.unban_user(user_id)
        await update.message.reply_text(f"User {user_id} has been unbanned.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    """Send a daily chore summary to the group chat."""
    global last_report_time

    if not REPORT_CHAT_ID:
        logger.warning("REPORT_CHAT_ID not set, skipping daily report")
        return

    since = last_report_time.astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")
    chores = await database.get_chores_since(since)

    if not chores:
        logger.info("No chores since last report, skipping")
        last_report_time = datetime.now(MANILA_TZ)
        await database.set_last_report_time(last_report_time.isoformat())
        return

    # Group by user
    user_chores = defaultdict(list)
    for chore in chores:
        name = chore["username"] or f"User {chore['user_id']}"
        user_chores[name].append(chore["chore_text"])

    # Format message
    today_str = datetime.now(MANILA_TZ).strftime("%a, %b %d")
    lines = [
        f"📋 **Daily Chore Summary**",
        f"📅 {today_str}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    for name, chores_list in user_chores.items():
        lines.append(f"🙋 **{name}** ({len(chores_list)} chore{'s' if len(chores_list) != 1 else ''})")
        for chore_text in chores_list:
            lines.append(f"• {chore_text}")
        lines.append("")

    total_chores = sum(len(v) for v in user_chores.values())
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(
        f"✅ {total_chores} chore{'s' if total_chores != 1 else ''} "
        f"completed by {len(user_chores)} person{'s' if len(user_chores) != 1 else ''}"
    )

    message = "\n".join(lines)

    try:
        await context.bot.send_message(chat_id=REPORT_CHAT_ID, text=message, parse_mode="Markdown")
        logger.info("Daily report sent")
    except Exception:
        logger.exception("Failed to send daily report")

    last_report_time = datetime.now(MANILA_TZ)
    await database.set_last_report_time(last_report_time.isoformat())


async def send_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    """Send a weekly chore summary every Monday covering the previous calendar week."""
    if not REPORT_CHAT_ID:
        logger.warning("REPORT_CHAT_ID not set, skipping weekly report")
        return

    now = datetime.now(MANILA_TZ)
    this_monday = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_monday = this_monday - timedelta(days=7)

    start_utc = last_monday.astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")
    end_utc = this_monday.astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")

    chores = await database.get_chores_between(start_utc, end_utc)

    if not chores:
        logger.info("No chores last week, skipping weekly report")
        return

    user_weekdays: dict[str, dict[str, list[str]]] = {}
    user_weekdays_order: list[str] = []

    for chore in chores:
        name = chore["username"] or f"User {chore['user_id']}"
        created_utc = datetime.strptime(chore["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        weekday = created_utc.astimezone(MANILA_TZ).strftime("%A")

        if name not in user_weekdays:
            user_weekdays[name] = {}
            user_weekdays_order.append(name)
        if weekday not in user_weekdays[name]:
            user_weekdays[name][weekday] = []
        user_weekdays[name][weekday].append(chore["chore_text"])

    week_start_str = last_monday.strftime("%b %d")
    week_end_str = (this_monday - timedelta(days=1)).strftime("%b %d")

    lines = [
        f"📋 **Weekly Chore Summary**",
        f"📅 {week_start_str} - {week_end_str}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for name in user_weekdays_order:
        lines.append(f"🙋 **{name}**")
        lines.append("")
        for day in WEEKDAYS:
            if day in user_weekdays[name]:
                lines.append(f"**{day}**")
                for ct in user_weekdays[name][day]:
                    lines.append(f"• {ct}")
                lines.append("")

    total_chores = sum(len(v) for d in user_weekdays.values() for v in d.values())
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(
        f"✅ {total_chores} chore{'s' if total_chores != 1 else ''} "
        f"completed by {len(user_weekdays)} person{'s' if len(user_weekdays) != 1 else ''} this week"
    )

    message = "\n".join(lines)

    try:
        await context.bot.send_message(chat_id=REPORT_CHAT_ID, text=message, parse_mode="Markdown")
        logger.info("Weekly report sent")
    except Exception:
        logger.exception("Failed to send weekly report")


async def post_init(app: Application):
    global last_report_time
    await database.init_db()

    # Restore last report time from database to survive restarts
    stored = await database.get_last_report_time()
    if stored:
        last_report_time = datetime.fromisoformat(stored)
    else:
        last_report_time = datetime.now(MANILA_TZ)
        await database.set_last_report_time(last_report_time.isoformat())

    logger.info("Last report time restored: %s", last_report_time)

    # Schedule daily report at 5 AM Manila time
    manila_5am = datetime.strptime("05:00", "%H:%M").replace(tzinfo=MANILA_TZ).time()
    app.job_queue.run_daily(
        send_daily_report,
        time=manila_5am,
        name="daily_report",
    )
    logger.info("Bot started — daily report scheduled at 5 AM Manila")

    # Schedule weekly report at 9 AM Monday Manila time
    manila_9am = datetime.strptime("09:00", "%H:%M").replace(tzinfo=MANILA_TZ).time()
    app.job_queue.run_daily(
        send_weekly_report,
        time=manila_9am,
        days=(0,),
        name="weekly_report",
    )
    logger.info("Weekly report scheduled at 9 AM Monday Manila")

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is required")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).job_queue(
        JobQueue(scheduler=BackgroundScheduler(timezone=MANILA_TZ))
    ).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chore", chore))
    app.add_handler(CommandHandler("chores", chores))
    app.add_handler(CommandHandler("clear", clear_chores))

    # Admin commands
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))

    # Callback query handler (quick chore buttons)
    app.add_handler(CallbackQueryHandler(handle_quick_chore))

    # Message handler (plain text = chore entry)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
