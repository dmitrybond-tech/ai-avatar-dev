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
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.markdown import hbold

import httpx
from pydantic import BaseModel

# Initialize dispatcher
dp = Dispatcher()

# Use uvloop on non-Windows platforms for performance
if os.name != "nt":
    with suppress(Exception):
        import uvloop  # type: ignore
        uvloop.install()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8080")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ru")
CAL_USERNAME = os.getenv("CAL_USERNAME", "dmitrybond")
CAL_EVENT_INTRO = os.getenv("CAL_EVENT_INTRO", "intro-30m")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")
BOT_NAME = os.getenv("TELEGRAM_BOT_NAME", "miniapp_bot")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://127.0.0.1:5173")  # optional for local dev

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("miniapp-bot")

# Bot mode: polling (default) or webhook
BOT_MODE = os.getenv("BOT_MODE", "polling")


class SessionState(BaseModel):
    lang: str = DEFAULT_LANG
    scene: str = "start"


# Simple in-memory sessions keyed by user id
_sessions: dict[int, SessionState] = {}


def get_session(user_id: int) -> SessionState:
    state = _sessions.get(user_id)
    if state is None:
        state = SessionState()
        _sessions[user_id] = state
    return state


async def fetch_rules(lang: str | None = None) -> dict:
    url = f"{API_BASE_URL}/rules"
    params = {"lang": lang} if lang else None
    timeout = httpx.Timeout(5.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def make_keyboard(labels: dict, scene_buttons: list[str], lang: str) -> InlineKeyboardMarkup:
    rows = []
    for key in scene_buttons:
        text = labels.get(key, key)
        # book button opens WebApp and has deep link fallback
        if key == "book":
            rows.append([
                InlineKeyboardButton(text=text, web_app=WebAppInfo(url=WEBAPP_URL)),
            ])
        else:
            rows.append([
                InlineKeyboardButton(text=text, callback_data=f"nav:{key}")
            ])
    # utility row: language toggle and back when not start
    rows.append([
        InlineKeyboardButton(text=labels.get("language", "Language"), callback_data="lang:toggle"),
        InlineKeyboardButton(text=labels.get("back", "Back"), callback_data="nav:start"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(Command("healthz"))
async def cmd_healthz(message: Message) -> None:
    await message.answer("ok")


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command with WebApp button."""
    user_id = message.from_user.id if message.from_user else 0
    logger.info(f"User {user_id} started the bot")
    
    # Create WebApp button
    web_app = WebAppInfo(url=f"{WEBAPP_URL}/miniapp/")
    button = KeyboardButton(text="Open Mini App", web_app=web_app)
    keyboard = ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)
    
    await message.answer(
        "Привет! Открывай мини-апп 👇",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("lang:"))
async def on_lang_toggle(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id if cb.from_user else 0
    session = get_session(user_id)
    session.lang = "en" if session.lang == "ru" else "ru"
    await cb.answer("Language switched")
    await show_scene(cb, session.scene)


@dp.callback_query(F.data.startswith("nav:"))
async def on_nav(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id if cb.from_user else 0
    session = get_session(user_id)
    target = cb.data.split(":", 1)[1]
    session.scene = target if target in {"start", "about", "services", "cases", "book"} else "start"
    if target == "book":
        url = f"https://cal.com/{CAL_USERNAME}/{CAL_EVENT_INTRO}"
        await cb.message.answer(f"{hbold('Cal.com')}: {url}")
        await cb.answer()
        return
    await cb.answer()
    await show_scene(cb, session.scene)


async def show_scene(cb: CallbackQuery | Message, scene_key: str) -> None:
    user_id = cb.from_user.id if getattr(cb, "from_user", None) else 0
    session = get_session(user_id)
    rules = await fetch_rules(session.lang)
    labels = rules.get("labels", {})
    scenes = rules.get("scenes", {})
    scene = scenes.get(scene_key, scenes.get("start", {}))
    text = scene.get("text", "")
    kb = make_keyboard(labels, scene.get("buttons", []), session.lang)
    if isinstance(cb, CallbackQuery):
        await cb.message.edit_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    else:
        await cb.answer(text, reply_markup=kb)


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
            BOT_MODE = "polling"
        
        if BOT_MODE == "polling":
            # Ensure webhook is not set (ignore errors)
            try:
                await bot.delete_webhook(drop_pending_updates=False)
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
