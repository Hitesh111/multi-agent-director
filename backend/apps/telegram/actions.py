import asyncio
import logging
from django.conf import settings
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# NOTE: We do NOT cache a global bot instance here.
# Celery uses a prefork process pool — the parent process forks workers after
# importing modules. A cached Bot shares its httpx connection pool across forks,
# causing two failures in the worker child processes:
#   1. "Event loop is closed" — asyncio.run() closes the loop; the next call
#      finds the same closed loop on the next task.
#   2. "Pool timeout: All connections in the connection pool are in use" — the
#      httpx pool inside the shared Bot is exhausted after the first send.
# Fix: create a fresh Bot (and therefore a fresh httpx pool) on every call.


def _get_token() -> str | None:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured")
        return None
    return token


async def send_telegram_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> bool:
    """Async send — for use inside the Telegram bot's own event loop."""
    token = _get_token()
    if not token:
        return False
    try:
        async with Bot(token=token) as bot:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
        return True
    except TelegramError as e:
        logger.exception("Failed to send Telegram message to %s: %s", chat_id, e)
        return False


def send_telegram_message_sync(chat_id: int, text: str, parse_mode: str | None = None) -> bool:
    """Sync send — safe to call from Celery worker tasks after asyncio.run() exits.

    Creates a fresh event loop and a fresh Bot instance every time to avoid
    the 'Event loop is closed' and 'Pool timeout' errors that occur when a
    shared Bot / shared loop is reused across forked worker processes.
    """
    token = _get_token()
    if not token:
        return False
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _send():
                async with Bot(token=token) as bot:
                    await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)

            loop.run_until_complete(_send())
        finally:
            loop.close()
        return True
    except TelegramError as e:
        logger.exception("Failed to send Telegram message to %s: %s", chat_id, e)
        return False
    except Exception as e:
        logger.exception("Unexpected error sending Telegram message to %s: %s", chat_id, e)
        return False
