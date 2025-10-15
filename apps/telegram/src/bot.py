"""Telegram bot main entry point."""
import logging
from telegram.ext import Application, CommandHandler
from settings import settings
from webapp import start_command, app_command

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    logger.info("Starting Telegram bot...")

    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("app", app_command))

    # Start polling
    logger.info("Bot is running in polling mode")
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()

