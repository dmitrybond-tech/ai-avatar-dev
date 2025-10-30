import json
import os
import threading
from typing import Any


class I18N:
    def __init__(self, locales_dir: str, default_lang: str = "ru", supported_langs: str | None = None) -> None:
        self._lock = threading.RLock()
        self._locales: dict[str, dict[str, str]] = {}
        self._default_lang = (default_lang or "ru").lower()
        self._supported = set((supported_langs or "ru,en").split(","))
        self._load_locales(locales_dir)

    def _load_locales(self, locales_dir: str) -> None:
        with self._lock:
            for lang in ("ru", "en"):
                path = os.path.join(locales_dir, f"{lang}.json")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self._locales[lang] = json.load(f)
                except Exception:
                    self._locales[lang] = {}

    def resolve_lang(self, user_id: int, stored_pref: str | None, profile_lang: str | None) -> str:
        candidates: list[str] = []
        if stored_pref:
            candidates.append(stored_pref.lower())
        if profile_lang:
            candidates.append(profile_lang.split("-")[0].lower())
        candidates.append(self._default_lang)
        for c in candidates:
            if c in self._supported:
                return c
        return self._default_lang

    def t(self, lang: str, key: str, **kwargs: Any) -> str:
        with self._lock:
            parts = key.split(".")
            cur: Any = self._locales.get(lang, {})
            for p in parts:
                cur = cur.get(p, {}) if isinstance(cur, dict) else {}
            if not isinstance(cur, str) or not cur:
                # fallback to default language
                cur = self._get_default(key)
            try:
                return cur.format(**kwargs) if isinstance(cur, str) else str(cur)
            except Exception:
                return str(cur)

    def _get_default(self, key: str) -> str:
        parts = key.split(".")
        cur: Any = self._locales.get(self._default_lang, {})
        for p in parts:
            cur = cur.get(p, {}) if isinstance(cur, dict) else {}
        return cur if isinstance(cur, str) else key



