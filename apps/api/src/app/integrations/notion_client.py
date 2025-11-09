"""Shared Notion client factory with backward-compatible timeout handling."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from httpx import Timeout
from notion_client import Client

from app.core.logging import get_logger

logger = get_logger(__name__)


def _normalize_timeout(timeout: Optional[int]) -> Optional[int]:
    """Normalize timeout value to a positive integer or None."""
    if timeout is None:
        return None
    try:
        value = int(timeout)
    except (TypeError, ValueError) as exc:  # pragma: no cover - validation guard
        raise ValueError("timeout must be an integer") from exc
    if value <= 0:
        return None
    return value


@lru_cache(maxsize=4)
def get_notion_client(api_key: str, timeout: Optional[int] = None) -> Client:
    """
    Construct a Notion client reusing instances per API key/timeout.

    The `notion-client` package changed the preferred timeout argument from
    integers (`timeout` / `timeout_ms`) to an `httpx.Timeout` instance. For
    compatibility we attempt the modern signature first and silently fall back
    to `Client(auth=...)` when older versions reject the keyword argument with
    a `TypeError`.
    """
    auth = (api_key or "").strip()
    if not auth:
        raise ValueError("Notion API key is not set")

    timeout_seconds = _normalize_timeout(timeout)

    attempts: tuple[dict[str, object], ...]
    if timeout_seconds:
        httpx_timeout = Timeout(timeout=timeout_seconds)
        attempts = (
            {"auth": auth, "timeout": httpx_timeout},
            {"auth": auth, "timeout": timeout_seconds},
            {"auth": auth},
        )
    else:
        attempts = ({"auth": auth},)

    last_error: Exception | None = None
    for attempt_kwargs in attempts:
        try:
            return Client(**attempt_kwargs)
        except TypeError as exc:
            # Older notion-client builds reject unknown timeout kwargs.
            last_error = exc
            logger.debug(
                "notion_client_factory_timeout_kwarg_unsupported",
                extra={"attempt_kwargs": list(attempt_kwargs.keys())},
            )
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("Failed to construct Notion client")


def clear_client_cache() -> None:
    """Reset cached Notion client instances (used by tests)."""
    get_notion_client.cache_clear()


