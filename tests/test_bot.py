from datetime import datetime

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.ext import ContextTypes

import bot
from bot import chore, chores, clear_chores, handle_message, start, send_daily_report, send_weekly_report

def make_update(text, user_id=123, username="alice"):
    user = MagicMock()
    user.id = user_id
    user.first_name = "Alice"
    user.username = username

    msg = MagicMock()
    msg.text = text
    msg.reply_text = AsyncMock()

    update = MagicMock()
    update.message = msg
    update.effective_user = user
    update.effective_chat = MagicMock(id=0)
    return update

@pytest.mark.asyncio
async def test_chore_command():
    update = make_update("/chore washed dishes")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = ["washed", "dishes"]

    with patch("bot.database.is_banned", new_callable=AsyncMock) as mock_banned:
        with patch("bot.database.add_chore", new_callable=AsyncMock) as mock_add:
            mock_banned.return_value = False
            await chore(update, context)

            mock_add.assert_called_once_with(123, "alice", "washed dishes")
            update.message.reply_text.assert_called_once_with("✅ Logged")

@pytest.mark.asyncio
async def test_chore_command_no_text():
    update = make_update("/chore")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []

    with patch("bot.database.is_banned", new_callable=AsyncMock) as mock_banned:
        mock_banned.return_value = False
        await chore(update, context)
        response = update.message.reply_text.call_args[0][0]
        assert "What did you do" in response

@pytest.mark.asyncio
async def test_handle_message_logs_chore():
    update = make_update("did the laundry")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    with patch("bot.database.is_banned", new_callable=AsyncMock) as mock_banned:
        with patch("bot.database.add_chore", new_callable=AsyncMock) as mock_add:
            mock_banned.return_value = False
            await handle_message(update, context)

            mock_add.assert_called_once_with(123, "alice", "did the laundry")
            update.message.reply_text.assert_called_once_with("✅ Logged")

@pytest.mark.asyncio
async def test_clear_chores():
    update = make_update("/clear")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    with patch("bot.database.is_banned", new_callable=AsyncMock) as mock_banned:
        with patch("bot.database.clear_chores", new_callable=AsyncMock) as mock_clear:
            mock_banned.return_value = False
            mock_clear.return_value = 5
            await clear_chores(update, context)

            mock_clear.assert_called_once_with(123)
            response = update.message.reply_text.call_args[0][0]
            assert "Cleared 5" in response

@pytest.mark.asyncio
async def test_start_command():
    update = make_update("/start")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    with patch("bot.database.is_banned", new_callable=AsyncMock) as mock_banned:
        mock_banned.return_value = False
        await start(update, context)
        response = update.message.reply_text.call_args[0][0]
        assert "Hi" in response
        assert "chores" in response.lower()

@pytest.mark.asyncio
async def test_banned_user():
    update = make_update("did something")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    with patch("bot.database.is_banned", new_callable=AsyncMock) as mock_banned:
        mock_banned.return_value = True
        await handle_message(update, context)

        response = update.message.reply_text.call_args[0][0]
        assert "banned" in response.lower()

@pytest.mark.asyncio
async def test_send_daily_report_formats_summary():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()

    bot.last_report_time = datetime(2024, 1, 1, tzinfo=bot.MANILA_TZ)

    mock_chores = [
        {"user_id": 1, "username": "alice", "chore_text": "washed dishes", "created_at": "2024-01-01T10:00:00"},
        {"user_id": 1, "username": "alice", "chore_text": "vacuumed", "created_at": "2024-01-01T14:00:00"},
        {"user_id": 2, "username": "bob", "chore_text": "cooked dinner", "created_at": "2024-01-01T18:00:00"},
    ]

    with patch("bot.REPORT_CHAT_ID", "12345"):
        with patch("bot.database.get_chores_since", new_callable=AsyncMock) as mock_since:
            mock_since.return_value = mock_chores
            await send_daily_report(context)

            context.bot.send_message.assert_called_once()
            call_kwargs = context.bot.send_message.call_args[1]
            text = call_kwargs["text"]

            assert "Daily Chore Summary" in text
            assert "📅" in text
            assert "━━━━━━━━━━━━━━━━━━━━" in text
            assert "alice" in text
            assert "washed dishes" in text
            assert "vacuumed" in text
            assert "bob" in text
            assert "cooked dinner" in text
            assert "(2 chore" in text
            assert "(1 chore)" in text
            assert "3 chores completed by 2 persons" in text
            assert call_kwargs["parse_mode"] == "Markdown"

@pytest.mark.asyncio
async def test_send_daily_report_skips_without_report_chat_id():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    with patch("bot.REPORT_CHAT_ID", None):
        await send_daily_report(context)
        # Should not raise and should not send

@pytest.mark.asyncio
async def test_send_daily_report_skips_when_no_chores():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()

    bot.last_report_time = datetime(2024, 1, 1, tzinfo=bot.MANILA_TZ)

    with patch("bot.REPORT_CHAT_ID", "12345"):
        with patch("bot.database.get_chores_since", new_callable=AsyncMock) as mock_since:
            mock_since.return_value = []
            await send_daily_report(context)

            context.bot.send_message.assert_not_called


@pytest.mark.asyncio
async def test_send_weekly_report_formats_summary():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()

    mock_chores = [
        {"user_id": 1, "username": "alice", "chore_text": "washed dishes", "created_at": "2024-06-10 01:00:00"},
        {"user_id": 1, "username": "alice", "chore_text": "vacuumed", "created_at": "2024-06-11 05:00:00"},
        {"user_id": 2, "username": "bob", "chore_text": "cooked dinner", "created_at": "2024-06-12 10:00:00"},
    ]

    with patch("bot.REPORT_CHAT_ID", "12345"):
        with patch("bot.database.get_chores_between", new_callable=AsyncMock) as mock_between:
            mock_between.return_value = mock_chores
            await send_weekly_report(context)

            context.bot.send_message.assert_called_once()
            call_kwargs = context.bot.send_message.call_args[1]
            text = call_kwargs["text"]

            assert "Weekly Chore Summary" in text
            assert "alice" in text
            assert "bob" in text
            assert "washed dishes" in text
            assert "vacuumed" in text
            assert "cooked dinner" in text
            assert "Monday" in text
            assert "Tuesday" in text
            assert "Wednesday" in text
            assert "this week" in text
            assert call_kwargs["parse_mode"] == "Markdown"


@pytest.mark.asyncio
async def test_send_weekly_report_skips_without_report_chat_id():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    with patch("bot.REPORT_CHAT_ID", None):
        await send_weekly_report(context)


@pytest.mark.asyncio
async def test_send_weekly_report_skips_when_no_chores():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()

    with patch("bot.REPORT_CHAT_ID", "12345"):
        with patch("bot.database.get_chores_between", new_callable=AsyncMock) as mock_between:
            mock_between.return_value = []
            await send_weekly_report(context)

            context.bot.send_message.assert_not_called
