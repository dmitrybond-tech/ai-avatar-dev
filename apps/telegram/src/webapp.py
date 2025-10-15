"""WebApp button handlers."""
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from settings import settings


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        f"👋 Welcome to AI Avatar!\n\n"
        f"I'm your personal AI assistant. Use /app to open the chat interface.",
    )


async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /app command - show Web App button."""
    keyboard = [
        [
            InlineKeyboardButton(
                "🤖 Open AI Avatar",
                web_app=WebAppInfo(url=settings.tg_webapp_url)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Click the button below to start chatting:",
        reply_markup=reply_markup,
    )

