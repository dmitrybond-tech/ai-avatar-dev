import asyncio
import json
import logging
import os
from contextlib import suppress
from datetime import datetime, timezone
from typing import Literal

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
    ReplyKeyboardRemove,
)
from aiogram.client.default import DefaultBotProperties
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

DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ru")
SUPPORTED_LANGS = os.getenv("SUPPORTED_LANGS", "ru,en")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")
BOT_NAME = os.getenv("TELEGRAM_BOT_NAME", "miniapp_bot")
TELEGRAM_MINIAPP_URL = os.getenv("TELEGRAM_MINIAPP_URL", "").strip()
TELEGRAM_BOOKING_URL = os.getenv("TELEGRAM_BOOKING_URL", "").strip()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("miniapp-bot")

# Bot mode: polling (default) or webhook
BOT_MODE = os.getenv("BOT_MODE", "polling")

# Helpers
_here = os.path.dirname(__file__)
_locales_dir = os.path.join(os.path.dirname(_here), "miniapp-bot", "locales")
# Fallback if relative path differs when run via repo root
if not os.path.isdir(_locales_dir):
    _locales_dir = os.path.join(_here, "locales")

i18n = I18N(locales_dir=_locales_dir, default_lang=DEFAULT_LANG, supported_langs=SUPPORTED_LANGS)
bot_state = UserStateStore(base_dir="/data/state")
notion_client = NotionClient()

MenuLocale = Literal["ru", "en"]
_empty_menu_warning_logged = False


def _log_menu_configuration() -> None:
    summary = (
        f"miniapp_url={'set' if TELEGRAM_MINIAPP_URL else 'empty'}(len:{len(TELEGRAM_MINIAPP_URL)}) "
        f"booking_url={'set' if TELEGRAM_BOOKING_URL else 'empty'}(len:{len(TELEGRAM_BOOKING_URL)})"
    )
    logger.info("menu.config %s", summary)
    if not TELEGRAM_MINIAPP_URL:
        logger.warning(
            "menu.button.miniapp.disabled",
            extra={"missing_env": "TELEGRAM_MINIAPP_URL"},
        )
    if not TELEGRAM_BOOKING_URL:
        logger.warning(
            "menu.button.booking.disabled",
            extra={"missing_env": "TELEGRAM_BOOKING_URL"},
        )


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


def _ensure_menu_locale(lang: str) -> MenuLocale:
    return "ru" if lang == "ru" else "en"


def build_main_menu(locale: MenuLocale) -> InlineKeyboardMarkup:
    global _empty_menu_warning_logged

    rows: list[list[InlineKeyboardButton]] = []
    if TELEGRAM_MINIAPP_URL:
        rows.append([
            InlineKeyboardButton(
                text=i18n.t(locale, "buttons.open_app"),
                web_app=WebAppInfo(url=TELEGRAM_MINIAPP_URL),
            )
        ])
    if TELEGRAM_BOOKING_URL:
        rows.append([
            InlineKeyboardButton(
                text=i18n.t(locale, "buttons.book"),
                url=TELEGRAM_BOOKING_URL,
            )
        ])
    if not rows:
        if not _empty_menu_warning_logged:
            logger.warning("menu.buttons.empty", extra={"envs": ["TELEGRAM_MINIAPP_URL", "TELEGRAM_BOOKING_URL"]})
            _empty_menu_warning_logged = True
        return InlineKeyboardMarkup(inline_keyboard=[])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _send_menu_hint(
    message: Message,
    lang: str,
    text_key: str = "menu.hint",
) -> None:
    locale = _ensure_menu_locale(lang)
    reply_markup = build_main_menu(locale)
    await message.answer(
        i18n.t(locale, text_key),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


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
    await _send_menu_hint(message, session.lang)


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


@dp.message(Command("book"))
@dp.message(F.text.in_({"Записаться", "Book a slot", "Book a call"}))
async def on_book(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    if TELEGRAM_BOOKING_URL:
        await message.answer(
            i18n.t(session.lang, "menu.booking_link", url=TELEGRAM_BOOKING_URL),
            reply_markup=build_main_menu(_ensure_menu_locale(session.lang)),
            disable_web_page_preview=False,
        )
    else:
        await _send_menu_hint(message, session.lang, text_key="menu.booking_unavailable")


@dp.message(Command("skills"))
@dp.message(F.text.in_({"Навыки", "Skills"}))
async def on_skills(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    await _send_menu_hint(message, session.lang)


@dp.message(Command("status", "statuses"))
@dp.message(F.text.in_({"Статусы", "Statuses"}))
async def on_statuses(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    await _send_menu_hint(message, session.lang)


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
        if TELEGRAM_BOOKING_URL:
            await cb.message.answer(
                i18n.t(session.lang, "menu.booking_link", url=TELEGRAM_BOOKING_URL),
                reply_markup=build_main_menu(_ensure_menu_locale(session.lang)),
                disable_web_page_preview=False,
            )
        else:
            await _send_menu_hint(cb.message, session.lang, text_key="menu.booking_unavailable")
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
    await message.answer(
        i18n.t(lang, "start.confirm_language"),
        reply_markup=ReplyKeyboardRemove(),
    )
    await _send_menu_hint(message, session.lang, text_key="menu.welcome")


@dp.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    await _send_menu_hint(message, session.lang)


@dp.message(Command("debug_menu"))
async def cmd_debug_menu(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    locale = _ensure_menu_locale(session.lang)
    payload = {
        "miniapp_url": "set" if TELEGRAM_MINIAPP_URL else "empty",
        "booking_url": "set" if TELEGRAM_BOOKING_URL else "empty",
        "locale": locale,
    }
    await message.answer(
        json.dumps(payload, ensure_ascii=False),
        reply_markup=build_main_menu(locale),
        disable_web_page_preview=True,
    )


@dp.message(Command("tz"))
@dp.message(F.text.func(lambda t: t == i18n.t("ru", "buttons.brief") or t == i18n.t("en", "buttons.brief")))
async def on_brief_button(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    session = get_session(user_id)
    await _send_menu_hint(message, session.lang)


@dp.message(F.document | F.photo | F.text)
async def on_any_message(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if user_id not in _awaiting_brief:
        return
    session = get_session(user_id)
    _awaiting_brief.discard(user_id)

    username = message.from_user.username if message.from_user else ""
    full_name = (message.from_user.full_name if message.from_user else "").strip()
    language_code = (message.from_user.language_code if message.from_user else None) or "—"
    # Telegram provides message.date in UTC; normalize and format ISO8601 with Z
    try:
        msg_dt = message.date
        if msg_dt.tzinfo is None:
            msg_dt = msg_dt.replace(tzinfo=timezone.utc)
        sent_at_utc = msg_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        sent_at_utc = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    caption = (message.caption or message.text or "") if message else ""

    file_id: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    file_url: str | None = None
    file_unique_id: str | None = None
    mime_type: str | None = None
    photo_width: int | None = None
    photo_height: int | None = None

    # Extract file info
    try:
        if message.document:
            file_id = message.document.file_id
            file_unique_id = message.document.file_unique_id
            file_name = message.document.file_name
            file_size = message.document.file_size
            mime_type = message.document.mime_type
        elif message.photo:
            # largest photo
            ph = message.photo[-1]
            file_id = ph.file_id
            file_unique_id = ph.file_unique_id
            file_size = getattr(ph, "file_size", None)
            photo_width = getattr(ph, "width", None)
            photo_height = getattr(ph, "height", None)
    except Exception:
        pass

    # Forward/copy to admin and send metadata
    try:
        admin_id = await resolve_admin_chat_id(bot)
        # Always copy the original message to preserve content/caption
        await forward_brief_to_admin(message, admin_id, bot)

        # Build metadata HTML
        username_disp = f"@{username}" if username else "—"
        name_disp = full_name or "—"
        file_block_lines: list[str] = []
        if message.document:
            file_block_lines.append(f"• <b>File:</b> name={file_name or '—'} mime={mime_type or '—'} size={file_size or '—'}")
            if file_id:
                file_block_lines.append(f"• <b>file_id:</b> {file_id}")
            if file_unique_id:
                file_block_lines.append(f"• <b>file_unique_id:</b> {file_unique_id}")
        elif message.photo:
            size_part = f" size={file_size}" if file_size is not None else ""
            dims_part = f" {photo_width or '—'}x{photo_height or '—'}" if (photo_width or photo_height) else ""
            file_block_lines.append(f"• <b>Photo:</b>{dims_part}{size_part}")
            if file_id:
                file_block_lines.append(f"• <b>file_id:</b> {file_id}")
            if file_unique_id:
                file_block_lines.append(f"• <b>file_unique_id:</b> {file_unique_id}")
        file_block = ("\n" + "\n".join(file_block_lines)) if file_block_lines else ""

        meta = (
            "<b>Brief metadata</b>\n"
            f"• <b>User ID:</b> {user_id}\n"
            f"• <b>Username:</b> {username_disp}\n"
            f"• <b>Name:</b> {name_disp}\n"
            f"• <b>Lang:</b> {language_code}\n"
            f"• <b>Sent at (UTC):</b> {sent_at_utc}"
            f"{file_block}"
        )
        await bot.send_message(admin_id, meta, parse_mode='HTML', disable_web_page_preview=True)
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
        iso_ts = sent_at_utc
        title = f"Brief: {username or str(user_id)} {iso_ts[:10]}"
        payload = {
            "title": title,
            # legacy fields retained
            "language": session.lang,
            "timestamp": iso_ts,
            "caption": caption,
            "file_id": file_id or "",
            "file_name": file_name or "",
            "file_size": file_size or None,
            "tg_username": username or "",
            "tg_user_id": user_id,
            "file_url": file_url or "",
            # extended metadata
            "sender_id": user_id,
            "username": username or "",
            "full_name": full_name or "",
            "language_code": language_code or "",
            "sent_at": iso_ts,
            "source_chat_id": message.chat.id if getattr(message, "chat", None) else None,
            "source_message_id": message.message_id,
            "mime_type": mime_type or "",
            "file_unique_id": file_unique_id or "",
            "photo_width": photo_width,
            "photo_height": photo_height,
        }
        notion_page_id: str | None = None
        if notion_client.configured():
            notion_page_id = await notion_client.create_brief_page(payload)
        logger.info(
            "brief.handle.success",
            extra={
                "sender_id": user_id,
                "username": username or "",
                "sent_at": iso_ts,
                "has_file": bool(file_id),
                "notion_page_id": notion_page_id,
            },
        )
    except Exception as e:
        logger.error(f"Failed to create Notion page for brief: {e}")

    await message.answer(
        i18n.t(session.lang, "brief.received"),
        reply_markup=build_main_menu(_ensure_menu_locale(session.lang)),
    )


async def main() -> None:
    """Main function with webhook/polling mode support."""
    _log_menu_configuration()
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
