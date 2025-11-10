from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Dict

logger = logging.getLogger(__name__)
_warned: set[str] = set()


def _warn_once(legacy_key: str, new_key: str) -> None:
    if legacy_key in _warned:
        return
    _warned.add(legacy_key)
    logger.warning("env:%s is deprecated; migrate to %s", legacy_key, new_key)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def notion_token() -> str | None:
    primary = _clean(os.getenv("NOTION_API_KEY"))
    if primary:
        return primary
    legacy = _clean(os.getenv("NOTION_SECRET"))
    if legacy:
        _warn_once("NOTION_SECRET", "NOTION_API_KEY")
    return legacy


def skills_db() -> str | None:
    primary = _clean(os.getenv("NOTION_DB_SKILLS"))
    if primary:
        return primary
    legacy = _clean(os.getenv("NOTION_DB"))
    if legacy:
        _warn_once("NOTION_DB", "NOTION_DB_SKILLS")
    return legacy


def tasks_db() -> str | None:
    primary = _clean(os.getenv("NOTION_PUBLIC_TASKS_DB_ID"))
    if primary:
        return primary
    legacy = _clean(os.getenv("NOTION_DB"))
    if legacy:
        _warn_once("NOTION_DB", "NOTION_PUBLIC_TASKS_DB_ID")
    return legacy


def notion_timeout() -> int:
    raw = _clean(os.getenv("NOTION_TIMEOUT"))
    if not raw:
        return 10
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning("env:NOTION_TIMEOUT invalid=%s default=10", raw)
        return 10
    return max(1, min(value, 300))


def _fmt(value: str | None) -> str:
    return f"SET(len:{len(value)})" if value else "EMPTY"


@lru_cache(maxsize=1)
def snapshot() -> Dict[str, str]:
    token = notion_token()
    skills = skills_db()
    tasks = tasks_db()
    return {
        "token": _fmt(token),
        "skills_db": _fmt(skills),
        "tasks_db": _fmt(tasks),
    }


