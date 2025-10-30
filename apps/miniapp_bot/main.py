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

from .i18n import I18N
from .state import UserStateStore
from .admin import resolve_admin_chat_id, forward_brief_to_admin
from .notion import NotionClient

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
notion_client = NotionClient()


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
    url = f"{API_BASE_URL}/rules"
    params = None
    timeout = httpx.Timeout(5.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

async def fetch_tasks() -> dict:
    url = f"{API_BASE_URL}/tasks/status"
    timeout = httpx.Timeout(5.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
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
    """Handle /start: show language selector and main keyboard."""
    user_id = message.from_user.id if message.from_user else 0
    profile_lang = (message.from_user.language_code if message.from_user else None) or None
    session = get_session(user_id)
    # resolve lang preference
    stored = bot_state.get_lang(user_id)
    lang = i18n.resolve_lang(user_id, stored, profile_lang)
    session.lang = lang

    # Language selection keyboard
    lang_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Русский"), KeyboardButton(text="English")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(i18n.t(lang, "start.choose_language"), reply_markup=lang_kb)


@dp.message(Command("language"))
async def cmd_language(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    lang_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Русский"), KeyboardButton(text="English")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(i18n.t(session.lang, "start.choose_language"), reply_markup=lang_kb)


@dp.message(F.text.in_({"Записаться", "Book a call"}))
async def on_book(message: Message) -> None:
    url = f"https://cal.com/{CAL_USERNAME}/{CAL_EVENT_INTRO}"
    await message.answer(f"Ссылка для записи: {url}")


@dp.message(F.text.in_({"Навыки", "Skills"}))
async def on_skills(message: Message) -> None:
    data = await fetch_rules()
    items = data.get("items", [])
    if not items:
        await message.answer("Пока нет данных.")
        return
    lines = ["Мои навыки:"]
    for it in items:
        title = it.get("title")
        desc = it.get("desc")
        tags = it.get("tags") or []
        tag_str = f" ({', '.join(tags)})" if tags else ""
        lines.append(f"• {title}{tag_str}" + (f" — {desc}" if desc else ""))
    await message.answer("\n".join(lines))


@dp.message(F.text.in_({"Статусы", "Statuses"}))
async def on_statuses(message: Message) -> None:
    data = await fetch_tasks()
    items = data.get("items", [])
    if not items:
        await message.answer("Пока нет задач.")
        return
    lines = ["Статусы задач:"]
    for it in items:
        lines.append(f"• {it.get('title')} — {it.get('status')}")
    await message.answer("\n".join(lines))


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
    # Minimal no-op to retain handler; new flows use fallback buttons
    if isinstance(cb, CallbackQuery):
        await cb.answer()


# In-memory awaiting brief flags
_awaiting_brief: set[int] = set()


def _main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    web_app = WebAppInfo(url=f"{WEBAPP_URL}/")
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.t(lang, "buttons.open_app"), web_app=web_app)],
            [
                KeyboardButton(text=i18n.t(lang, "buttons.book")),
                KeyboardButton(text=i18n.t(lang, "buttons.skills")),
                KeyboardButton(text=i18n.t(lang, "buttons.statuses"))
            ],
            [KeyboardButton(text=i18n.t(lang, "buttons.brief"))],
        ],
        resize_keyboard=True,
    )


@dp.message(F.text.in_({"Русский", "English"}))
async def on_language_choice(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    choice = (message.text or "").lower()
    lang = "ru" if "рус" in choice else "en"
    # validate against supported langs
    if lang not in set(SUPPORTED_LANGS.split(",")):
        lang = DEFAULT_LANG
    bot_state.set_lang(user_id, lang)
    session.lang = lang
    await message.answer(i18n.t(lang, "start.confirm_language"), reply_markup=_main_keyboard(lang))


@dp.message(F.text.func(lambda t: t == i18n.t("ru", "buttons.brief") or t == i18n.t("en", "buttons.brief")))
async def on_brief_button(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    _awaiting_brief.add(user_id)
    await message.answer(i18n.t(session.lang, "brief.prompt_upload"))


@dp.message(F.document | F.photo | F.text)
async def on_any_message(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if user_id not in _awaiting_brief:
        return
    session = get_session(user_id)
    _awaiting_brief.discard(user_id)

    username = message.from_user.username if message.from_user else ""
    caption = (message.caption or message.text or "") if message else ""

    file_id: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    file_url: str | None = None

    # Extract file info
    try:
        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name
            file_size = message.document.file_size
        elif message.photo:
            # largest photo
            ph = message.photo[-1]
            file_id = ph.file_id
            file_size = ph.file_size
    except Exception:
        pass

    # Forward/copy to admin
    try:
        admin_id = await resolve_admin_chat_id(bot)
        if file_id:
            await forward_brief_to_admin(message, admin_id, bot)
        else:
            await bot.send_message(chat_id=admin_id, text=f"Brief text from @{username} ({user_id}):\n{caption}")
    except Exception as e:
        logger.error(f"Failed to forward brief to admin: {e}")
        await message.answer(i18n.t(session.lang, "errors.try_again"))
        return

    # Build Bot API file URL if possible
    try:
        if file_id:
            file = await bot.get_file(file_id)
            if getattr(file, "file_path", None):
                token = os.getenv("TELEGRAM_TOKEN", "")
                if token:
                    file_url = f"https://api.telegram.org/file/bot{token}/{file.file_path}"
    except Exception:
        file_url = None

    # Create Notion page (best-effort)
    try:
        iso_ts = __import__("datetime").datetime.utcnow().isoformat()
        title = f"Brief from @{username} ({user_id})" if username else f"Brief from {user_id}"
        payload = {
            "title": title,
            "language": session.lang,
            "timestamp": iso_ts,
            "caption": caption,
            "file_id": file_id or "",
            "file_name": file_name or "",
            "file_size": file_size or None,
            "tg_username": username or "",
            "tg_user_id": user_id,
            "file_url": file_url or "",
        }
        if notion_client.configured():
            await notion_client.create_brief_page(payload)
    except Exception as e:
        logger.error(f"Failed to create Notion page for brief: {e}")

    await message.answer(i18n.t(session.lang, "brief.received"), reply_markup=_main_keyboard(session.lang))


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


