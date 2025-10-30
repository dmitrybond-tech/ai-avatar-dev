import json
import os
import threading
import tempfile
from typing import Optional


class UserStateStore:
    def __init__(self, base_dir: str = "/data/state") -> None:
        self._lock = threading.RLock()
        self._users_path = os.path.join(base_dir, "users.json")
        os.makedirs(os.path.dirname(self._users_path), exist_ok=True)
        if not os.path.exists(self._users_path):
            self._atomic_write({})

    def _atomic_write(self, data: dict) -> None:
        with self._lock:
            dir_name = os.path.dirname(self._users_path)
            fd, tmp_path = tempfile.mkstemp(prefix="users_", suffix=".json", dir=dir_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self._users_path)
            finally:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass

    def _load(self) -> dict:
        with self._lock:
            try:
                with open(self._users_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}

    def get_lang(self, user_id: int) -> Optional[str]:
        data = self._load()
        u = data.get(str(user_id)) or {}
        lang = u.get("lang")
        return str(lang) if isinstance(lang, str) else None

    def set_lang(self, user_id: int, lang: str) -> None:
        with self._lock:
            data = self._load()
            entry = data.get(str(user_id)) or {}
            entry["lang"] = lang
            data[str(user_id)] = entry
            self._atomic_write(data)


