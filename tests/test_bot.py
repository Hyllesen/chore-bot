import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.ext import ContextTypes

from bot import chore, chores, clear_chores, handle_message, start

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
            update.message.reply_text.assert_called_once()
            response = update.message.reply_text.call_args[0][0]
            assert "washed dishes" in response

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
            update.message.reply_text.assert_called_once()

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
