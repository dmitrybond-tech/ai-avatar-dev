import os
import logging
from aiogram import Bot


logger = logging.getLogger("miniapp-bot")


_cached_admin_chat_id: int | None = None


async def resolve_admin_chat_id(bot: Bot) -> int:
    global _cached_admin_chat_id
    if _cached_admin_chat_id is not None:
        return _cached_admin_chat_id

    username = "@d1mab0nd"
    try:
        chat = await bot.get_chat(username)
        if getattr(chat, "id", None):
            _cached_admin_chat_id = int(chat.id)
            return _cached_admin_chat_id
    except Exception as e:
        logger.warning(f"Failed to resolve admin by username: {e}")

    env_val = os.getenv("ADMIN_CHAT_ID")
    if env_val:
        try:
            _cached_admin_chat_id = int(env_val)
            return _cached_admin_chat_id
        except Exception:
            logger.error("ADMIN_CHAT_ID is set but not a valid integer")

    raise RuntimeError("Cannot resolve admin chat id: set ADMIN_CHAT_ID or ensure @d1mab0nd is resolvable")


