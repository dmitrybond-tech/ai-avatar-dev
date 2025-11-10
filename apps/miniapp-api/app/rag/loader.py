from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DEFAULT_CSV_PATH = Path("/app/data/skills.csv")
SUPPORTED_LANGS = ("en", "ru")


@dataclass(frozen=True)
class SkillRecord:
    id: str
    lang: str
    title: str
    short: Optional[str]
    tags: List[str]
    bullets: List[str]
    examples: List[str]
    slug: str


class SkillsCache:
    """Simple in-memory cache keyed by CSV mtime."""

    def __init__(self) -> None:
        self._mtime: Optional[float] = None
        self._records: List[SkillRecord] = []

    def load(self) -> List[SkillRecord]:
        csv_path = resolve_csv_path()
        try:
            mtime = csv_path.stat().st_mtime
        except FileNotFoundError as exc:  # pragma: no cover - caught during runtime
            raise FileNotFoundError(f"Skills CSV not found at {csv_path}") from exc

        if self._records and self._mtime == mtime:
            return self._records

        self._records = _read_csv(csv_path)
        self._mtime = mtime
        return self._records

    @property
    def mtime(self) -> Optional[float]:
        return self._mtime


_cache = SkillsCache()


def resolve_csv_path() -> Path:
    configured = os.getenv("SKILLS_CSV_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_CSV_PATH


def source_mtime() -> Optional[float]:
    """Return the cached mtime (after the first `load_skills` call)."""
    return _cache.mtime


def load_skills() -> List[SkillRecord]:
    return _cache.load()


def _split_multi(value: str) -> List[str]:
    if not value:
        return []
    lines = [line.strip() for line in value.replace("\r\n", "\n").split("\n")]
    return [line for line in lines if line]


def _split_tags(value: str) -> List[str]:
    if not value:
        return []
    tags = [item.strip() for item in value.split(",")]
    return [item for item in tags if item]


def _read_csv(path: Path) -> List[SkillRecord]:
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    records: List[SkillRecord] = []

    for idx, row in enumerate(rows):
        slug = (row.get("Slug") or row.get("slug") or "").strip()
        if not slug:
            slug = f"skill-{idx}"

        shared_tags = _split_tags(row.get("Tags") or row.get("tags") or "")

        entry = {
            "en": {
                "title": (row.get("Title EN") or row.get("title_en") or row.get("title_en_us") or "").strip(),
                "short": (row.get("Short EN") or row.get("short_en") or "").strip() or None,
                "bullets": _split_multi(row.get("Bullets EN") or row.get("bullets_en") or ""),
                "examples": _split_multi(row.get("Examples EN") or row.get("examples_en") or ""),
            },
            "ru": {
                "title": (row.get("Title RU") or row.get("title_ru") or "").strip(),
                "short": (row.get("Short RU") or row.get("short_ru") or "").strip() or None,
                "bullets": _split_multi(row.get("Bullets RU") or row.get("bullets_ru") or ""),
                "examples": _split_multi(row.get("Examples RU") or row.get("examples_ru") or ""),
            },
        }

        for lang in SUPPORTED_LANGS:
            title = entry[lang]["title"]
            if not title:
                continue
            record = SkillRecord(
                id=f"{slug}:{lang}",
                lang=lang,
                title=title,
                short=entry[lang]["short"],
                tags=shared_tags[:],
                bullets=entry[lang]["bullets"],
                examples=entry[lang]["examples"],
                slug=slug,
            )
            records.append(record)

    return records


