"""Dependency helpers exposed to FastAPI routers."""
from __future__ import annotations

from apps.miniapp_api.core.settings import Settings, SettingsError, get_settings as _get_settings


def get_settings() -> Settings:
    return _get_settings()


__all__ = ["Settings", "SettingsError", "get_settings"]



