"""Robust CSV skills loader with caching and mtime-based reload."""
from __future__ import annotations

import csv
import logging
import os
import re
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

import pandas as pd
from rapidfuzz import process

from ..core import env as env_utils

logger = logging.getLogger(__name__)

# CSV header aliases for tolerant ingestion
# Supports exact headers: Title EN, Bullets EN, Bullets RU, Examples EN, Examples RU, Short EN, Short RU, Slug, Tags, Title RU
CSV_ALIASES = {
    "key": ["slug", "key", "id"],
    "title_en": ["title en", "title_en", "name_en", "en_title", "en_name", "title"],
    "title_ru": ["title ru", "title_ru", "name_ru", "ru_title", "ru_name"],
    "short_en": ["short en", "short_en", "summary_en", "en_short", "en_summary"],
    "short_ru": ["short ru", "short_ru", "summary_ru", "ru_short", "ru_summary"],
    "tags": ["tags", "labels", "categories"],
    "bullets_en": ["bullets en", "bullets_en", "points_en", "en_bullets"],
    "bullets_ru": ["bullets ru", "bullets_ru", "points_ru", "ru_bullets"],
    "examples_en": ["examples en", "examples_en", "cases_en", "en_examples", "example_en"],
    "examples_ru": ["examples ru", "examples_ru", "cases_ru", "ru_examples", "example_ru"],
    "weight": ["weight", "order", "prio", "rank"],
    "pinned": ["pinned", "pin", "featured"],
}


def _h(row: Dict[str, str], key: str) -> str:
    """Get value from row using CSV_ALIASES, return empty string if not found.
    Assumes row keys are already normalized to lowercase."""
    for name in CSV_ALIASES[key]:
        name_lower = name.lower()
        if name_lower in row and row[name_lower] is not None:
            val = row[name_lower]
            return str(val).strip() if val else ""
    return ""


def _split_list(val: str) -> List[str]:
    """Split tags by ; or ,; trim spaces; de-dup."""
    if not val:
        return []
    parts = [p.strip() for p in re.split(r"[;,]", val) if p.strip()]
    return parts


def _split_lines(val: str) -> List[str]:
    """Split bullets/examples by \\n; drop empty lines; trim. Handles \\n unescape and real newlines in CSV."""
    if not val:
        return []
    # Normalize line endings
    text = val.replace("\r\n", "\n")
    # Handle literal \n sequences first
    if "\\n" in text:
        # literal '\n' case
        lines = [p.strip() for p in text.split("\\n") if p.strip()]
    else:
        # real newlines
        lines = [p.strip() for p in text.splitlines() if p.strip()]
    return lines


def _to_bool(val: str) -> bool:
    """Coerce to bool: accepts 1/true/yes/y/да (case-insensitive)."""
    return str(val).strip().lower() in {"1", "true", "yes", "y", "да"}


def _to_int(val: str, default: int = 0) -> int:
    """Coerce to int with default fallback."""
    try:
        return int(str(val).strip())
    except (ValueError, AttributeError):
        return default


class SkillRecord:
    """Represents a single skill record from CSV."""

    def __init__(
        self,
        key: str,
        title_en: str,
        title_ru: str,
        short_en: str,
        short_ru: str,
        tags: List[str],
        bullets_en: List[str],
        bullets_ru: List[str],
        examples_en: List[str],
        examples_ru: List[str],
        weight: int = 0,
        pinned: bool = False,
    ):
        self.key = key
        self.title_en = title_en
        self.title_ru = title_ru
        self.short_en = short_en
        self.short_ru = short_ru
        self.tags = tags
        self.bullets_en = bullets_en
        self.bullets_ru = bullets_ru
        self.examples_en = examples_en
        self.examples_ru = examples_ru
        self.weight = weight
        self.pinned = pinned

    def title(self, lang: str) -> str:
        if lang.startswith("ru"):
            return self.title_ru or self.title_en or self.key
        return self.title_en or self.title_ru or self.key

    def summary(self, lang: str) -> str:
        if lang.startswith("ru"):
            return self.short_ru or self.short_en
        return self.short_en or self.short_ru

    def bullets(self, lang: str) -> List[str]:
        if lang.startswith("ru"):
            return self.bullets_ru or self.bullets_en
        return self.bullets_en or self.bullets_ru

    def examples(self, lang: str) -> List[str]:
        if lang.startswith("ru"):
            return self.examples_ru or self.examples_en
        return self.examples_en or self.examples_ru

    def to_dict(self, lang: Optional[str] = None) -> Dict:
        """Convert to API-compatible dict."""
        if lang:
            lang_key = "ru" if lang.startswith("ru") else "en"
            return {
                "slug": self.key,
                "title": self.title(lang_key),
                "short": self.summary(lang_key),
                "tags": self.tags,
                "bullets": self.bullets(lang_key),
                "examples": self.examples(lang_key),
            }
        return {
            "slug": self.key,
            "title_en": self.title_en,
            "title_ru": self.title_ru,
            "short_en": self.short_en,
            "short_ru": self.short_ru,
            "tags": self.tags,
            "bullets_en": self.bullets_en,
            "bullets_ru": self.bullets_ru,
            "examples_en": self.examples_en,
            "examples_ru": self.examples_ru,
            "weight": self.weight,
            "pinned": self.pinned,
        }


class SkillsLoader:
    """Robust CSV loader with caching and mtime-based reload."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._cache: Optional[List[SkillRecord]] = None
        self._cached_mtime: Optional[float] = None
        self._csv_path = self._resolve_csv_path()

    def _resolve_csv_path(self) -> Path:
        """Resolve CSV path from env or default."""
        csv_path_env = os.getenv("SKILLS_CSV_PATH")
        if csv_path_env:
            return Path(csv_path_env)
        # Default to /app/data/skills.csv (container path)
        return Path("/app/data/skills.csv")

    def _get_mtime(self) -> Optional[float]:
        """Get file modification time, or None if file doesn't exist."""
        if not self._csv_path.exists():
            return None
        try:
            return self._csv_path.stat().st_mtime
        except OSError:
            return None

    def _load_csv(self) -> List[SkillRecord]:
        """Load skills from CSV with UTF-8 BOM handling and robust parsing using pandas."""
        csv_path = self._csv_path
        if not csv_path.exists():
            logger.warning("Skills CSV path %s does not exist", csv_path)
            return []

        items: List[SkillRecord] = []
        encoding_used = None
        try:
            # Try UTF-8 with BOM first, then fallback to UTF-8
            encodings = ["utf-8-sig", "utf-8"]
            df = None

            for enc in encodings:
                try:
                    # Use pandas with python engine for robust handling of quoted multiline cells
                    # on_bad_lines parameter available in pandas >= 1.3.0
                    read_kwargs = {
                        "encoding": enc,
                        "engine": "python",
                        "quotechar": '"',
                        "skipinitialspace": True,
                        "keep_default_na": False,  # Don't treat empty strings as NaN
                    }
                    # Try with on_bad_lines for newer pandas, fallback to error_bad_lines for older
                    try:
                        df = pd.read_csv(csv_path, **read_kwargs, on_bad_lines="skip")
                    except TypeError:
                        # Fallback for older pandas versions
                        try:
                            df = pd.read_csv(csv_path, **read_kwargs, error_bad_lines=False, warn_bad_lines=False)
                        except TypeError:
                            # Even older pandas - remove keep_default_na if not supported
                            read_kwargs.pop("keep_default_na", None)
                            df = pd.read_csv(csv_path, **read_kwargs, error_bad_lines=False, warn_bad_lines=False)
                    encoding_used = enc
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as exc:
                    logger.warning("Failed to read CSV %s with encoding %s: %s", csv_path, enc, exc)
                    continue

            if df is None or df.empty:
                logger.error("Failed to decode CSV %s with any encoding or CSV is empty", csv_path)
                return []

            # Normalize column names to lowercase for case-insensitive matching
            df.columns = df.columns.str.lower().str.strip()

            # Convert DataFrame to list of dicts
            normalized_rows = df.to_dict("records")

            for i, row in enumerate(normalized_rows):
                # Convert all values to strings, handling NaN and None
                row_str = {}
                for k, v in row.items():
                    key_lower = str(k).lower().strip()
                    # Handle NaN/None/empty: convert to empty string
                    if pd.isna(v) or v is None:
                        row_str[key_lower] = ""
                    else:
                        # Convert to string and strip
                        row_str[key_lower] = str(v).strip()

                key = _h(row_str, "key") or f"skill_{i}"
                title_en = _h(row_str, "title_en") or key
                title_ru = _h(row_str, "title_ru") or title_en
                short_en = _h(row_str, "short_en")
                short_ru = _h(row_str, "short_ru") or short_en
                tags = _split_list(_h(row_str, "tags"))
                bullets_en = _split_lines(_h(row_str, "bullets_en"))
                bullets_ru = _split_lines(_h(row_str, "bullets_ru"))
                examples_en = _split_lines(_h(row_str, "examples_en"))
                examples_ru = _split_lines(_h(row_str, "examples_ru"))
                weight = _to_int(_h(row_str, "weight"), 0)
                pinned = _to_bool(_h(row_str, "pinned"))

                # Skip rows without at least one title
                if not (title_en or title_ru):
                    logger.debug("Skipping row %d: no title_en or title_ru", i)
                    continue

                items.append(
                    SkillRecord(
                        key=key,
                        title_en=title_en,
                        title_ru=title_ru,
                        short_en=short_en,
                        short_ru=short_ru,
                        tags=tags,
                        bullets_en=bullets_en,
                        bullets_ru=bullets_ru,
                        examples_en=examples_en,
                        examples_ru=examples_ru,
                        weight=weight,
                        pinned=pinned,
                    )
                )
        except Exception as exc:
            logger.error("skills_csv_read_failed: Failed to read CSV %s: %s", csv_path, exc, exc_info=True)
            return []

        # Stable ordering: pinned desc, weight desc, key asc
        items.sort(key=lambda s: (-int(getattr(s, "pinned", False)), -int(getattr(s, "weight", 0)), s.key))
        logger.info("Loaded %d skills from CSV %s (encoding=%s)", len(items), csv_path, encoding_used)
        return items

    def get_skills(self, lang: Optional[str] = None) -> List[SkillRecord]:
        """Get all skills, optionally filtered by language."""
        skills = self.load_skills()
        return skills  # Language filtering can be done at API level

    def find_skill(self, slug: str) -> Optional[SkillRecord]:
        """Find a skill by slug."""
        skills = self.load_skills()
        return next((s for s in skills if s.key == slug), None)

    def search_skills(self, query: str, lang: Optional[str] = None, top_k: int = 5) -> List[SkillRecord]:
        """Search skills using fuzzy matching."""
        skills = self.load_skills()
        if not skills or not query:
            return skills[:top_k] if skills else []

        # Build searchable text for each skill
        def skill_text(skill: SkillRecord) -> str:
            lang_key = lang or "en"
            parts = [
                skill.title(lang_key),
                skill.summary(lang_key),
                " ".join(skill.tags),
                " ".join(skill.bullets(lang_key)[:3]),
                " ".join(skill.examples(lang_key)[:2]),
            ]
            return " ".join(parts).lower()

        # Use rapidfuzz to find best matches
        skill_texts = {i: skill_text(s) for i, s in enumerate(skills)}
        matches = process.extract(
            query.lower(),
            skill_texts,
            limit=top_k,
            score_cutoff=0,  # Return all matches, sorted by score
        )

        # Return skills in order of match score
        result = [skills[idx] for score, idx, _ in matches if score > 0]
        return result[:top_k]

    def load_skills(self) -> List[SkillRecord]:
        """Load skills with caching based on file mtime."""
        with self._lock:
            current_mtime = self._get_mtime()

            # Check if we need to reload
            if self._cache is None or self._cached_mtime != current_mtime:
                self._cache = self._load_csv()
                self._cached_mtime = current_mtime

            return self._cache.copy() if self._cache else []


# Global singleton instance
_loader_instance: Optional[SkillsLoader] = None


def get_loader() -> SkillsLoader:
    """Get or create the global skills loader instance."""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = SkillsLoader()
    return _loader_instance


# Convenience functions matching the API
def get_skills(lang: Optional[str] = None) -> List[SkillRecord]:
    """Get all skills."""
    return get_loader().get_skills(lang)


def find_skill(slug: str) -> Optional[SkillRecord]:
    """Find a skill by slug."""
    return get_loader().find_skill(slug)


def search_skills(query: str, lang: Optional[str] = None, top_k: int = 5) -> List[SkillRecord]:
    """Search skills using fuzzy matching."""
    return get_loader().search_skills(query, lang, top_k)

