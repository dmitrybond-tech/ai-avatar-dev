from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd
from rapidfuzz import fuzz

try:
    from notion_client import Client  # type: ignore
except Exception:  # pragma: no cover - notion client is optional
    Client = None  # type: ignore

from ..core import env as env_utils

logger = logging.getLogger(__name__)

# CSV header aliases for tolerant ingestion
# Supports exact headers: Title EN, Bullets EN, Bullets RU, Examples EN, Examples RU, Short EN, Short RU, Slug, Tags, Title RU
CSV_ALIASES = {
    "key": ["key", "slug", "id", "slug"],
    "title_en": ["title_en", "name_en", "en_title", "en_name", "title", "title en"],
    "title_ru": ["title_ru", "name_ru", "ru_title", "ru_name", "title ru"],
    "short_en": ["short_en", "summary_en", "en_short", "en_summary", "short en"],
    "short_ru": ["short_ru", "summary_ru", "ru_short", "ru_summary", "short ru"],
    "tags": ["tags", "labels", "categories"],
    "bullets_en": ["bullets_en", "points_en", "en_bullets", "bullets en"],
    "bullets_ru": ["bullets_ru", "points_ru", "ru_bullets", "bullets ru"],
    "examples_en": ["examples_en", "cases_en", "en_examples", "example_en", "examples en"],
    "examples_ru": ["examples_ru", "cases_ru", "ru_examples", "example_ru", "examples ru"],
    "weight": ["weight", "order", "prio"],
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
    parts = [p.strip(" \t\r\n-•") for p in val.replace(";", ",").split(",")]
    return [p for p in parts if p]


def _split_lines(val: str) -> List[str]:
    """Split bullets/examples by \\n; drop empty lines; trim. Handles \\n unescape and real newlines in CSV."""
    if not val:
        return []
    # Handle literal \n sequences first
    text = val.replace("\\n", "\n")
    # Split by actual newlines (handles multi-line CSV cells)
    lines = [l.strip(" \t\r\n-•") for l in text.splitlines()]
    return [l for l in lines if l]


def _to_bool(val: str) -> bool:
    """Coerce to bool: accepts 1/true/yes/y/да (case-insensitive)."""
    return str(val).strip().lower() in {"1", "true", "yes", "y", "да"}


def _to_int(val: str, default: int = 0) -> int:
    """Coerce to int with default fallback."""
    try:
        return int(str(val).strip())
    except (ValueError, AttributeError):
        return default


def _clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _split_tags(value: object) -> List[str]:
    text = _clean(value)
    if not text:
        return []
    tokens = [token.strip() for token in text.replace(";", ",").split(",")]
    return [token for token in tokens if token]


@dataclass(frozen=True)
class SkillRecord:
    key: str
    title_en: str
    title_ru: str
    short_en: str
    short_ru: str
    bullets_en: List[str]
    bullets_ru: List[str]
    examples_en: List[str]
    examples_ru: List[str]
    tags: List[str]
    source: str
    weight: int = 0
    pinned: bool = False

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

@dataclass
class SkillsSnapshot:
    skills: List[SkillRecord]
    source: str
    notion: bool
    csv_fallback: bool


class SkillsRepository:
    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshot: Optional[SkillsSnapshot] = None

        self._notion_api_key = env_utils.notion_token()
        self._notion_db = env_utils.skills_db()
        self._notion_timeout = float(env_utils.notion_timeout())

        default_csv = Path(__file__).resolve().parent.parent.parent / "data" / "skills.csv"
        self._csv_path = Path(os.getenv("SKILLS_CSV_PATH") or "/app/data/skills.csv" or str(default_csv))
        self._source = (os.getenv("SKILLS_SOURCE") or "auto").strip().lower()

    def refresh(self) -> SkillsSnapshot:
        with self._lock:
            self._snapshot = self._load_snapshot()
            return self._snapshot

    def snapshot(self) -> SkillsSnapshot:
        with self._lock:
            if self._snapshot is None:
                self._snapshot = self._load_snapshot()
            return self._snapshot

    def _load_snapshot(self) -> SkillsSnapshot:
        src = self._source
        csv_file = self._csv_path
        use_notion = bool(os.getenv("NOTION_API_KEY") and os.getenv("NOTION_DB_SKILLS"))
        skills: List[SkillRecord] = []
        notion_ok = False
        csv_used = False

        if src == "csv":
            skills = _load_csv(csv_file)
            csv_used = True
        elif src == "notion":
            skills, notion_ok = self._load_from_notion()
            # Fallback to CSV if Notion fails
            if not skills:
                skills = _load_csv(csv_file)
                csv_used = True
        else:  # auto
            if use_notion:
                skills, notion_ok = self._load_from_notion()
            if not skills:
                skills = _load_csv(csv_file)
                csv_used = True

        logger.info(
            "Loaded %s skills (source=%s, notion=%s, csv=%s, mode=%s)",
            len(skills),
            "csv" if csv_used else ("notion" if notion_ok else "unknown"),
            notion_ok,
            csv_used,
            src,
        )
        return SkillsSnapshot(
            skills=skills,
            source="csv" if csv_used else ("notion" if notion_ok else "unknown"),
            notion=notion_ok,
            csv_fallback=csv_used,
        )

    # Notion helpers -----------------------------------------------------

    def _load_from_notion(self) -> tuple[List[SkillRecord], bool]:
        """Load from Notion, return (records, success)."""
        if not self._notion_api_key or not self._notion_db or Client is None:
            return [], False
        try:
            client = Client(auth=self._notion_api_key, timeout=self._notion_timeout)
        except Exception as exc:  # pragma: no cover - network auth failure
            logger.warning("Failed to init Notion client: %s", exc)
            return [], False

        try:
            response = client.databases.query(database_id=self._notion_db)  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - network failure
            logger.warning("Notion query failed: %s", exc)
            return [], False
        results = response.get("results", [])

        records: List[SkillRecord] = []
        for row in results:
            props = row.get("properties", {})
            title_en = _plain_text(props, ["Title EN", "Name", "Title"])
            title_ru = _plain_text(props, ["Title RU", "Title Ru", "Title"])
            short_en = _plain_text(props, ["Short EN", "Summary"])
            short_ru = _plain_text(props, ["Short RU", "Short"])
            slug = _plain_text(props, ["Slug"])
            if not slug:
                slug = _slugify(_clean(title_en or title_ru or ""))
            tags = _multi_select(props, ["Tags", "Tag"])
            bullets_en = _rich_text(props, ["Bullets EN", "Bullets"])
            bullets_ru = _rich_text(props, ["Bullets RU"])
            examples_en = _rich_text(props, ["Examples EN", "Examples"])
            examples_ru = _rich_text(props, ["Examples RU"])

            if not (title_en or title_ru):
                continue

            records.append(
                SkillRecord(
                    key=slug or _slugify(title_en or title_ru),
                    title_en=title_en or title_ru,
                    title_ru=title_ru or title_en,
                    short_en=short_en or short_ru,
                    short_ru=short_ru or short_en,
                    bullets_en=bullets_en or examples_en,
                    bullets_ru=bullets_ru or examples_ru,
                    examples_en=examples_en or bullets_en,
                    examples_ru=examples_ru or bullets_ru,
                    tags=tags,
                    source="notion",
                    weight=0,
                    pinned=False,
                )
            )
        return records, len(records) > 0

    # Ranking ------------------------------------------------------------

    def relevant_skills(self, query: str, top_k: int) -> List[SkillRecord]:
        snapshot = self.snapshot()
        if not snapshot.skills:
            return []
        cleaned_query = _clean(query).lower()
        if not cleaned_query:
            return snapshot.skills[:top_k]

        scored = []
        for skill in snapshot.skills:
            corpus = " ".join(
                [
                    skill.title_en,
                    skill.title_ru,
                    skill.short_en,
                    skill.short_ru,
                    " ".join(skill.tags),
                    " ".join(skill.bullets_en[:3]),
                    " ".join(skill.bullets_ru[:3]),
                    " ".join(skill.examples_en[:2]),
                    " ".join(skill.examples_ru[:2]),
                ]
            ).lower()
            score = fuzz.token_set_ratio(cleaned_query, corpus)
            if score > 0:
                scored.append((score, skill))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [skill for _, skill in scored[:top_k]]


def _load_csv(path: Path) -> List[SkillRecord]:
    """Load skills from CSV with tolerant header aliases."""
    if not path.exists():
        logger.warning("Skills CSV path %s does not exist", path)
        return []
    items: List[SkillRecord] = []
    try:
        # Try UTF-8 with BOM first, then fallback to UTF-8
        encodings = ["utf-8-sig", "utf-8"]
        content = None
        encoding_used = None
        
        for enc in encodings:
            try:
                with path.open(encoding=enc, newline="") as f:
                    content = f.read()
                    encoding_used = enc
                    break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            logger.error("Failed to decode CSV %s with any encoding", path)
            return []
        
        # Parse CSV content
        import io
        rdr = csv.DictReader(io.StringIO(content))
        # Normalize row keys to lowercase for case-insensitive matching
        normalized_rows = []
        for row in rdr:
            normalized = {str(k).lower(): v for k, v in row.items()}
            normalized_rows.append(normalized)
        
        for i, row in enumerate(normalized_rows):
            key = _h(row, "key") or f"skill_{i}"
            title_en = _h(row, "title_en") or key
            title_ru = _h(row, "title_ru") or title_en
            short_en = _h(row, "short_en")
            short_ru = _h(row, "short_ru") or short_en
            tags = _split_list(_h(row, "tags"))
            bullets_en = _split_lines(_h(row, "bullets_en"))
            bullets_ru = _split_lines(_h(row, "bullets_ru"))
            examples_en = _split_lines(_h(row, "examples_en"))
            examples_ru = _split_lines(_h(row, "examples_ru"))
            weight = _to_int(_h(row, "weight"), 0)
            pinned = _to_bool(_h(row, "pinned"))

            if not (title_en or title_ru):
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
                    source="csv",
                )
            )
    except Exception as exc:  # pragma: no cover - csv failure
        logger.warning("Failed to read CSV %s: %s", path, exc)
        return []

    # stable ordering: pinned desc, weight desc, key asc
    items.sort(key=lambda s: (-int(getattr(s, "pinned", False)), -int(getattr(s, "weight", 0)), s.key))
    logger.info("Loaded %d skills from CSV %s (encoding=%s)", len(items), path, encoding_used)
    return items


def _slugify(text: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "skill"


def _plain_text(props: dict, keys: Sequence[str]) -> str:
    for key in keys:
        candidate = props.get(key)
        if not candidate:
            continue
        typ = candidate.get("type")
        if typ == "title":
            items = candidate.get("title", [])
            texts = [item.get("plain_text", "") for item in items if item]
            joined = "".join(texts).strip()
            if joined:
                return joined
        if typ == "rich_text":
            items = candidate.get("rich_text", [])
            texts = [item.get("plain_text", "") for item in items if item]
            joined = "".join(texts).strip()
            if joined:
                return joined
        if typ == "formula":
            string_val = candidate.get("formula", {}).get("string")
            if string_val:
                return str(string_val).strip()
    return ""


def _multi_select(props: dict, keys: Sequence[str]) -> List[str]:
    for key in keys:
        candidate = props.get(key)
        if not candidate:
            continue
        if candidate.get("type") == "multi_select":
            return [item.get("name", "").strip() for item in candidate.get("multi_select", []) if item.get("name")]
    return []


def _rich_text(props: dict, keys: Sequence[str]) -> List[str]:
    lines: List[str] = []
    for key in keys:
        candidate = props.get(key)
        if not candidate:
            continue
        array = candidate.get(candidate.get("type", ""), [])
        for block in array or []:
            text = block.get("plain_text") or block.get("text", {}).get("content")
            if not text:
                continue
            for line in text.splitlines():
                cleaned = line.strip(" •-\t")
                if cleaned:
                    lines.append(cleaned)
    return lines


def best_query_from_messages(messages: Iterable[str]) -> str:
    texts = [text.strip() for text in messages if text and text.strip()]
    if not texts:
        return ""
    if len(texts) == 1:
        return texts[0]
    return " ".join(texts[-3:])

