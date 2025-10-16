"""Telegram Bot for Mini App - Long Polling."""
import os
import logging
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN must be set")
if not WEBAPP_URL:
    raise ValueError("WEBAPP_URL must be set")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - show WebApp button."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    # Create WebApp button
    web_app = WebAppInfo(url=WEBAPP_URL)
    button = KeyboardButton(text="🤖 Open Assistant", web_app=web_app)
    keyboard = ReplyKeyboardMarkup([[button]], resize_keyboard=True)
    
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        f"Welcome to the AI Avatar assistant.\n\n"
        f"Tap the button below to open the Mini App and start chatting!",
        reply_markup=keyboard
    )


def main() -> None:
    """Start the bot with long polling."""
    logger.info("Starting Telegram bot with long polling...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # Start long polling
    logger.info(f"Bot is running. WebApp URL: {WEBAPP_URL}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

