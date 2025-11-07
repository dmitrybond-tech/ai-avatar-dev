"""Telegram environment validation helpers."""

from __future__ import annotations

import json
import logging
import os
from typing import Iterable


logger = logging.getLogger("app.bootstrap_env")

REQUIRED_KEYS: tuple[str, ...] = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ADMIN_CHAT_ID",
)

OPTIONAL_KEYS: tuple[str, ...] = ("TELEGRAM_SEND_REQUIRED",)

LEGACY_MAP = {
    "TELEGRAM_BOT_TOKEN": "TELEGRAM_TOKEN",
    "TELEGRAM_ADMIN_CHAT_ID": "ADMIN_CHAT_ID",
}


def _lens(key: str) -> str:
    value = os.getenv(key, "")
    return f"{key}=SET(len:{len(value)})" if value else f"{key}=<EMPTY>"


def _log_lens(keys: Iterable[str]) -> None:
    for key in keys:
        message = _lens(key)
        level = logging.INFO if os.getenv(key) else logging.WARNING
        logger.log(level, message)


def _adopt_legacy() -> None:
    adopted: list[str] = []
    for canonical, legacy in LEGACY_MAP.items():
        if not os.getenv(canonical) and os.getenv(legacy):
            os.environ[canonical] = os.getenv(legacy, "")
            adopted.append(f"{legacy}->{canonical}")
    if adopted:
        logger.info("Adopted legacy Telegram env vars: %s", ", ".join(adopted))


def validate_env() -> None:
    """Validate Telegram environment configuration."""

    _adopt_legacy()

    _log_lens(REQUIRED_KEYS + OPTIONAL_KEYS)

    if is_strict_mode():
        missing = [key for key in REQUIRED_KEYS if not os.getenv(key)]
        if missing:
            logger.error("Strict Telegram send mode enabled but missing: %s", ", ".join(missing))
            raise RuntimeError("Strict Telegram send mode requires TELEGRAM_* variables")


def is_strict_mode() -> bool:
    return os.getenv("TELEGRAM_SEND_REQUIRED", "false").strip().lower() in {"1", "true", "yes"}


def ping_telegram_if_strict() -> None:
    """Ping Telegram getMe endpoint when strict mode is enabled."""

    if not is_strict_mode():
        return

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("Strict mode enabled but TELEGRAM_BOT_TOKEN missing before ping")
        raise RuntimeError("Strict mode enabled without TELEGRAM_BOT_TOKEN")

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - defensive branch
        raise RuntimeError("Strict Telegram send mode requires httpx") from exc

    url = f"https://api.telegram.org/bot{token}/getMe"
    logger.info("Pinging Telegram getMe endpoint (%s)", _lens("TELEGRAM_BOT_TOKEN"))

    try:
        response = httpx.get(url, timeout=5.0)
    except Exception as exc:  # pragma: no cover - network failure path
        logger.error("Telegram ping failed: %s", exc)
        raise RuntimeError("Telegram ping failed") from exc

    content_type = response.headers.get("content-type", "")
    payload: dict[str, object] | None = None
    if content_type.startswith("application/json"):
        payload = response.json()
    else:
        snippet = response.text[:200] if response.text else ""
        logger.warning("Unexpected content-type from Telegram: %s body=%s", content_type, snippet)

    if response.status_code != 200 or not (payload or {}).get("ok"):
        safe_body = json.dumps(payload) if payload is not None else response.text[:200]
        logger.error(
            "Telegram ping returned status=%s ok=%s", response.status_code, (payload or {}).get("ok")
        )
        raise RuntimeError(f"Telegram ping failed: status={response.status_code} body={safe_body}")

    logger.info("Telegram ping succeeded (ok=true)")

