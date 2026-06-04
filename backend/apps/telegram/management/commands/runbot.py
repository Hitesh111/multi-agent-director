import sys
import os
import time
import threading
import logging
from django.core.management.base import BaseCommand
from apps.telegram.bot import create_application
from apps.telegram.models import TelegramSettings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Start the Telegram bot polling loop"

    def handle(self, *args, **options):
        self.stdout.write("Starting Telegram bot polling with auto-restart...")

        try:
            db_settings = TelegramSettings.load()
            current_updated_at = db_settings.updated_at
        except Exception:
            current_updated_at = None

        def monitor_settings():
            while True:
                time.sleep(5)
                try:
                    new_settings = TelegramSettings.load()
                    if new_settings.updated_at != current_updated_at:
                        self.stdout.write("Settings changed! Restarting bot process...")
                        # Restart the current process to re-initialize with new settings
                        os.execv(sys.executable, ['python'] + sys.argv)
                except Exception as e:
                    pass

        # Start the background thread to monitor token changes
        monitor_thread = threading.Thread(target=monitor_settings, daemon=True)
        monitor_thread.start()

        try:
            application = create_application()
            self.stdout.write("Bot is running. Press Ctrl+C to stop.")
            application.run_polling(allowed_updates=["messages"])
        except ValueError as e:
            self.stdout.write(f"Cannot start bot: {e}. Waiting for configuration...")
            # If no token is set, we sleep infinitely.
            # The monitor thread will restart the process once a token is saved in the UI.
            while True:
                time.sleep(1)
