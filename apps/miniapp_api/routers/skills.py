from __future__ import annotations

import csv
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from notion_client import Client
from pydantic import ValidationError

from apps.miniapp_api.core.settings import get_settings
from apps.miniapp_api.services.skills_repo import Skill, SkillsRepository


log = logging.getLogger(__name__)

router = APIRouter(tags=["skills"])


def _normalize_lang(value: Optional[str]) -> str:
    return "ru" if (value or "").lower().startswith("ru") else "en"


def _resolve_skills_source() -> str:
    return (os.getenv("SKILLS_SOURCE") or "auto").strip().lower()


def _resolve_csv_path() -> Path:
    configured = (os.getenv("SKILLS_CSV_PATH") or "").strip()
    if configured:
        candidate = Path(configured)
        if not candidate.is_absolute():
            project_root = Path(__file__).resolve().parents[3]
            candidate = (project_root / candidate).resolve()
        return candidate
    default_path = Path(__file__).resolve().parents[2] / "api" / "data" / "skills.csv"
    return default_path.resolve()


def _split_lines(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    lines: List[str] = []
    for fragment in str(raw).replace("\r\n", "\n").split("\n"):
        cleaned = fragment.strip(" •-\t")
        if cleaned:
            lines.append(cleaned)
    return lines


def _split_tags(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [tag.strip() for tag in str(raw).split(",") if tag.strip()]


def _slugify(value: str) -> str:
    base = value.strip().lower()
    base = re.sub(r"[^a-z0-9\s\-]+", "", base)
    base = re.sub(r"[\s\-]+", "-", base).strip("-")
    return base or "skill"


def _load_csv_skills(lang: str) -> Tuple[List[Skill], Dict[str, Any]]:
    path = _resolve_csv_path()
    metadata: Dict[str, Any] = {"source": "csv"}

    if not path.exists():
        log.error("skills_csv_missing path=%s", path)
        metadata["error"] = "csv_missing"
        return [], metadata

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
    except Exception as exc:  # noqa: BLE001
        log.exception("skills_csv_read_failed path=%s", path)
        metadata["error"] = f"csv_error:{exc.__class__.__name__}"
        return [], metadata

    resolved_lang = _normalize_lang(lang)
    title_key = f"Title {'RU' if resolved_lang == 'ru' else 'EN'}"
    short_key = f"Short {'RU' if resolved_lang == 'ru' else 'EN'}"
    bullets_key = f"Bullets {'RU' if resolved_lang == 'ru' else 'EN'}"
    examples_key = f"Examples {'RU' if resolved_lang == 'ru' else 'EN'}"

    items: List[Skill] = []
    for index, row in enumerate(rows, start=1):
        title = (row.get(title_key) or row.get("Title EN") or row.get("Title RU") or "").strip()
        if not title:
            log.warning("skills_csv_skip_row_missing_title lang=%s row=%s", resolved_lang, index)
            continue

        short = (row.get(short_key) or row.get("Short EN") or row.get("Short RU") or title).strip()
        slug = (row.get("Slug") or "").strip() or _slugify(title)

        bullets = _split_lines(row.get(bullets_key) or row.get("Bullets") or "")
        examples = _split_lines(row.get(examples_key) or row.get("Examples") or "")
        tags = _split_tags(row.get("Tags"))

        order_value = row.get("Order")
        try:
            order = int(order_value) if order_value else index
        except (TypeError, ValueError):
            order = index

        skill = Skill(
            id=(row.get("ID") or slug or "").strip() or slug,
            slug=slug,
            title=title,
            category=None,
            level=None,
            short=short or title,
            long=None,
            tags=tags,
            order=order,
            bullets=bullets,
            examples=examples,
        )
        items.append(skill)

    items.sort(key=lambda item: ((item.order or 0), item.slug))
    metadata["count"] = len(items)
    return items, metadata


def _build_repo_or_raise() -> SkillsRepository:
    try:
        settings = get_settings()
        db_id = settings.NOTION_DB_SKILLS
        token = getattr(settings, "NOTION_API_KEY", None) or getattr(settings, "NOTION_SECRET", None)
        if not token or not db_id:
            raise HTTPException(status_code=500, detail="skills_config_missing")

        timeout = getattr(settings, "NOTION_TIMEOUT", 10)
        try:
            client = Client(auth=token, timeout_ms=int(timeout) * 1000)
        except TypeError:
            client = Client(auth=token, timeout=timeout)
        return SkillsRepository(client, db_id, timeout)
    except ValidationError:
        log.exception("skills_settings_validation_failed")
        raise HTTPException(status_code=500, detail="skills_settings_invalid")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("skills_repo_init_failed")
        raise HTTPException(status_code=500, detail=f"skills_repo_init_failed:{exc.__class__.__name__}") from exc


def _serialize(skill: Skill) -> Dict[str, Any]:
    data = skill.dict()
    if not data.get("short"):
        data["short"] = ""
    if not data.get("long"):
        data["long"] = None
    return data


def _collect_skills(resolved_lang: str) -> Tuple[List[Skill], Dict[str, Any], Optional[str]]:
    source_mode = _resolve_skills_source()

    if source_mode == "csv":
        items, meta = _load_csv_skills(resolved_lang)
        meta.setdefault("source", "csv")
        return items, meta, None

    try:
        repo = _build_repo_or_raise()
    except HTTPException as exc:
        if source_mode == "auto":
            log.warning("skills_config_missing_fallback_csv detail=%s", exc.detail)
            items, meta = _load_csv_skills(resolved_lang)
            meta.setdefault("source", "csv")
            return items, meta, str(exc.detail)
        raise

    try:
        items, meta = repo.get_skills(resolved_lang)
        meta.setdefault("source", "notion")
        return items, meta, None
    except Exception as exc:  # noqa: BLE001
        detail = f"notion_error:{exc.__class__.__name__}"
        log.exception("skills_fetch_failed")
        if source_mode == "auto":
            fallback_items, fallback_meta = _load_csv_skills(resolved_lang)
            fallback_meta.setdefault("source", "csv")
            log.warning("skills_fallback_to_csv lang=%s detail=%s", resolved_lang, detail)
            return fallback_items, fallback_meta, detail
        raise HTTPException(status_code=502, detail=detail) from exc


@router.get("/skills")
def skills(
    lang: str = Query("en", description="Language code (ru|en)"),
    _debug: int = Query(0, description="Return raw payload when set"),
):
    resolved_lang = _normalize_lang(lang)
    items, meta, error = _collect_skills(resolved_lang)
    if error and _debug:
        meta = {**meta, "fallback_error": error}

    payload = {
        "items": [_serialize(item) for item in items],
        "meta": {"lang": resolved_lang, **meta},
    }
    return payload


@router.get("/skills/{slug}")
def skill_detail(
    slug: str,
    lang: str = Query("en", description="Language code (ru|en)"),
):
    resolved_lang = _normalize_lang(lang)
    items, _, _ = _collect_skills(resolved_lang)
    for item in items:
        if item.slug == slug or item.id == slug:
            return _serialize(item)
    raise HTTPException(status_code=404, detail="skill_not_found")


@router.get("/_health/skills")
def health_skills() -> Dict[str, Any]:
    try:
        settings = get_settings()
        return {
            "ok": True,
            "env": {
                "has_db_id": bool(getattr(settings, "NOTION_DB_SKILLS", None)),
                "has_token": bool(
                    getattr(settings, "NOTION_API_KEY", None) or getattr(settings, "NOTION_SECRET", None)
                ),
            },
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": exc.__class__.__name__}


