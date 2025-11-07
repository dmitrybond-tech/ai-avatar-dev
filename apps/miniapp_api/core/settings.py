"""Application settings and validation helpers for the miniapp API."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import logging
try:  # pragma: no cover - compatibility shim
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - fallback for Pydantic v1
    from pydantic import BaseSettings  # type: ignore[attr-defined]

from pydantic import Field, root_validator, validator


logger = logging.getLogger(__name__)


class SettingsError(RuntimeError):
    """Raised when required configuration is missing or malformed."""


class Settings(BaseSettings):
    """Environment-driven settings for the miniapp API."""

    NOTION_API_KEY: Optional[str] = Field(default=None, env="NOTION_API_KEY")
    NOTION_SECRET: Optional[str] = Field(default=None, env="NOTION_SECRET")
    NOTION_DB_SKILLS: Optional[str] = Field(default=None, env="NOTION_DB_SKILLS")
    NOTION_TIMEOUT: int = Field(default=10, env="NOTION_TIMEOUT")

    class Config:
        env_file = None
        case_sensitive = False

    @validator("NOTION_TIMEOUT", pre=True)
    def _coerce_timeout(cls, value: object) -> int:  # noqa: D417
        if value in (None, ""):
            return 10
        try:
            timeout = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:  # noqa: PERF203
            raise ValueError("NOTION_TIMEOUT must be an integer") from exc
        if timeout < 1:
            raise ValueError("NOTION_TIMEOUT must be at least 1 second")
        # Keep cache-friendly upper bound to avoid excessively long waits
        if timeout > 120:
            logger.warning("NOTION_TIMEOUT=%s trimmed to 120s", timeout)
            return 120
        return timeout

    @root_validator(pre=True)
    def _strip_strings(cls, values: dict) -> dict:  # noqa: D417
        for key in ("NOTION_API_KEY", "NOTION_SECRET", "NOTION_DB_SKILLS"):
            raw = values.get(key)
            if isinstance(raw, str):
                values[key] = raw.strip() or None
        return values

    @property
    def notion_token(self) -> Optional[str]:
        return self.NOTION_API_KEY or self.NOTION_SECRET

    def ensure_skills_config(self) -> None:
        missing = []
        if not self.notion_token:
            missing.append("NOTION_API_KEY (or NOTION_SECRET)")
        if not self.NOTION_DB_SKILLS:
            missing.append("NOTION_DB_SKILLS")
        if missing:
            raise SettingsError(
                "Missing configuration: " + ", ".join(missing) + ". "
                "Set the required environment variables to enable skills sync from Notion."
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()



