import asyncio
import logging
import os
from contextlib import suppress

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.client.default import DefaultBotProperties
from pydantic import BaseModel

from .i18n import I18N
from .state import UserStateStore
# Brief/admin/Notion integrations removed from main flow

# Initialize dispatcher
dp = Dispatcher()

# Use uvloop on non-Windows platforms for performance
if os.name != "nt":
    with suppress(Exception):
        import uvloop  # type: ignore
        uvloop.install()

API_BASE_URL = os.getenv("API_BASE_URL", "https://miniapp.dmitrybond.tech")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ru")
SUPPORTED_LANGS = os.getenv("SUPPORTED_LANGS", "ru,en")
CAL_USERNAME = os.getenv("CAL_USERNAME", "dmitrybond")
CAL_EVENT_INTRO = os.getenv("CAL_EVENT_INTRO", "intro-30m")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")
BOT_NAME = os.getenv("TELEGRAM_BOT_NAME", "miniapp_bot")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://miniapp.dmitrybond.tech")
MINIAPP_URL = os.getenv("MINIAPP_URL", WEBAPP_URL)
CAL_URL = os.getenv("CAL_URL", f"https://cal.com/{os.getenv('CAL_USERNAME','dmitrybond')}/{os.getenv('CAL_EVENT_INTRO','intro-30m')}")
BRIEF_URL = os.getenv("BRIEF_URL", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("miniapp-bot")

# Bot mode: polling (default) or webhook
BOT_MODE = os.getenv("BOT_MODE", "polling")

# Helpers
_here = os.path.dirname(__file__)
_locales_dir = os.path.join(os.path.dirname(_here), "miniapp_bot", "locales")
# Fallback if relative path differs when run via repo root
if not os.path.isdir(_locales_dir):
    _locales_dir = os.path.join(_here, "locales")

i18n = I18N(locales_dir=_locales_dir, default_lang=DEFAULT_LANG, supported_langs=SUPPORTED_LANGS)
bot_state = UserStateStore(base_dir="/data/state")

# Hint: ensure @BotFather `/setdomain` matches MINIAPP_URL domain for WebApp buttons
try:
    _domain = __import__("urllib.parse").urlparse(MINIAPP_URL).netloc
    if _domain:
        logger.info(f"BOT: WebApp domain hint for @BotFather /setdomain: { _domain }")
except Exception:
    pass


class SessionState(BaseModel):
    lang: str = DEFAULT_LANG
    scene: str = "start"
    awaiting_brief: bool = False


# Simple in-memory sessions keyed by user id
_sessions: dict[int, SessionState] = {}


def get_session(user_id: int) -> SessionState:
    state = _sessions.get(user_id)
    if state is None:
        state = SessionState()
        _sessions[user_id] = state
    return state


async def fetch_rules() -> dict:
    # Deprecated: Skills removed from bot menu
    return {}

async def fetch_tasks() -> dict:
    # Deprecated: Statuses removed from bot menu
    return {}


def main_menu(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=i18n.t(lang, "menu.openMiniApp"), web_app=WebAppInfo(url=MINIAPP_URL))],
        [InlineKeyboardButton(text=i18n.t(lang, "menu.bookCall"), url=CAL_URL)],
        [InlineKeyboardButton(text=i18n.t(lang, "menu.brief"), url=BRIEF_URL or "https://example.com")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def language_menu() -> InlineKeyboardMarkup:
    """Create inline keyboard for language selection."""
    rows = [
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(Command("healthz"))
async def cmd_healthz(message: Message) -> None:
    await message.answer("ok")


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start: show language selection if no locale, otherwise show main menu."""
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    stored = bot_state.get_lang(user_id)
    
    # Check if user has explicitly chosen a language (stored in persistent state)
    if not stored:
        # No language chosen yet - show language selection
        # Use a default language for the "choose language" message itself
        profile_lang = (message.from_user.language_code if message.from_user else None) or None
        default_lang = i18n.resolve_lang(user_id, None, profile_lang)
        await message.answer(i18n.t(default_lang, "language.choose"), reply_markup=language_menu())
        return
    
    # Language is set - show main menu
    session.lang = stored
    await message.answer(i18n.t(session.lang, "messages.main"), reply_markup=main_menu(session.lang))


@dp.message(Command("language"))
async def cmd_language(message: Message) -> None:
    """Handle /language: always show language selection."""
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    # Use current session language or default for the "choose language" message
    lang = session.lang or DEFAULT_LANG
    await message.answer(i18n.t(lang, "language.choose"), reply_markup=language_menu())


# Removed: book via reply keyboard; now URL button is in inline menu


# Removed: skills command/menu


# Removed: statuses command/menu


# Removed: legacy inline language toggle


# Removed: legacy nav callbacks; main menu uses direct URLs/web_app


async def show_scene(cb: CallbackQuery | Message, scene_key: str) -> None:
    # Kept for backward compatibility; no-op
    if isinstance(cb, CallbackQuery):
        await cb.answer()


# In-memory awaiting brief flags
_awaiting_brief: set[int] = set()


# Removed: old ReplyKeyboard menu


@dp.callback_query(F.data.startswith("set_lang:"))
async def on_language_callback(callback: CallbackQuery) -> None:
    """Handle language selection callback."""
    user_id = callback.from_user.id if callback.from_user else 0
    lang_code = callback.data.split(":")[1] if ":" in callback.data else DEFAULT_LANG
    
    # Validate language
    if lang_code not in set(SUPPORTED_LANGS.split(",")):
        lang_code = DEFAULT_LANG
    
    # Save language to session and persistent storage
    session = get_session(user_id)
    session.lang = lang_code
    bot_state.set_lang(user_id, lang_code)
    
    # Answer callback query
    await callback.answer()
    
    # Try to edit the message, fallback to new message if edit fails
    if callback.message:
        try:
            await callback.message.edit_text(i18n.t(lang_code, "language.changed"))
        except Exception:
            # If edit fails, send a new message
            await callback.message.answer(i18n.t(lang_code, "language.changed"))
        
        # Send main menu
        await callback.message.answer(i18n.t(lang_code, "messages.main"), reply_markup=main_menu(lang_code))


# Removed: brief upload flow (now external URL)


# Removed: handling of document/photo/text for brief


async def main() -> None:
    """Main function with webhook/polling mode support."""
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    try:
        if BOT_MODE == "webhook":
            # Webhook mode (optional, behind env flag)
            webhook_url = os.getenv("WEBHOOK_URL")
            if not webhook_url:
                raise RuntimeError("WEBHOOK_URL must be set when BOT_MODE=webhook")
            
            # Set webhook
            await bot.set_webhook(webhook_url)
            logger.info(f"BOT: webhook set to {webhook_url}")
            
            # Start webhook server (this would need additional setup)
            # For now, we'll default to polling
            logger.warning("Webhook mode not fully implemented, falling back to polling")
        
        if BOT_MODE == "polling":
            # Ensure webhook is not set (ignore errors)
            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except Exception as e:
                logger.warning(f"Failed to delete webhook (this is ok): {e}")
            
            logger.info("BOT: polling started")
            # Start polling with only the updates we actually use
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            
    finally:
        await bot.session.close()


if __name__ == "main":  # unlikely, but keep parity
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())


