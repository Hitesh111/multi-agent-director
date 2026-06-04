import logging

from django.conf import settings
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from . import handlers

logger = logging.getLogger(__name__)


from .models import TelegramSettings

def create_application() -> Application:
    # Try database first
    try:
        db_settings = TelegramSettings.load()
        token = db_settings.bot_token
    except Exception:
        token = None

    if not token:
        # Fallback to env var
        token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not configured in settings or database")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("workflows", handlers.workflows_command))
    application.add_handler(CommandHandler("agents", handlers.agents_command))
    application.add_handler(CommandHandler("executions", handlers.executions_command))
    application.add_handler(CommandHandler("cancel", handlers.cancel_command))
    application.add_handler(CommandHandler("workflow", handlers.workflow_command))
    application.add_handler(
        MessageHandler(filters.PHOTO, handlers.handle_photo)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message)
    )

    logger.info("Telegram bot handlers registered")
    return application
