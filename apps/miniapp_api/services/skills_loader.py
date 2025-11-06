from __future__ import annotations

from typing import Any, Dict, List

import json
import logging
import os
import re

from apps.miniapp_api.core.env import notion_token, skills_db, notion_timeout


log = logging.getLogger(__name__)


def _slugify(title: str) -> str:
    base = (title or "").strip().lower()
    base = re.sub(r"[^a-z0-9\s\-]+", "", base)
    base = re.sub(r"[\s\-]+", "-", base).strip("-")
    return base or "untitled"


def _seed_path(lang: str) -> str:
    # Reuse seeds from the dash package: apps/miniapp-api/seed/skills.{lang}.json
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(repo_root, "miniapp-api", "seed", f"skills.{lang}.json")


def _read_seed(lang: str) -> List[Dict[str, Any]]:
    path = _seed_path(lang)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("Skills: failed to read seed %s: %s", path, e)
        return []


def _client():
    try:
        from notion_client import Client  # type: ignore
    except Exception:
        return None
    token = notion_token()
    if not token:
        return None
    try:
        return Client(auth=token, timeout=notion_timeout())
    except Exception:
        return None


def _fetch_skills_from_notion(db_id: str, token: str, lang: str, timeout: int) -> List[Dict[str, Any]]:
    # The client is recreated here to use provided args explicitly
    try:
        from notion_client import Client  # type: ignore
    except Exception:
        return []
    try:
        client = Client(auth=token, timeout=timeout)
        resp = client.databases.query(database_id=db_id)
        pages = resp.get("results", [])
    except Exception as e:
        log.warning("Skills: Notion query failed: %s", e)
        return []

    def _plain(rt: Dict[str, Any]) -> str:
        t = rt.get(rt.get("type", ""), [])
        if isinstance(t, list) and t:
            return "".join([x.get("plain_text", "") for x in t]).strip()
        return ""

    def _rich_to_lines(prop: Dict[str, Any]) -> List[str]:
        arr = prop.get(prop.get("type", ""), [])
        lines: List[str] = []
        for b in arr or []:
            txt = b.get("plain_text") or (b.get("text", {}) or {}).get("content") or ""
            if txt:
                for line in re.split(r"[\r\n]+", txt):
                    cleaned = line.strip(" •-\t")
                    if cleaned:
                        lines.append(cleaned)
        return lines

    items: List[Dict[str, Any]] = []
    for p in pages:
        props: Dict[str, Any] = p.get("properties", {})
        title_en = _plain(props.get("Title EN", {})) or _plain(props.get("Name", {}))
        title_ru = _plain(props.get("Title RU", {})) or title_en
        short_en = _plain(props.get("Short EN", {})) or _plain(props.get("Summary", {}))
        short_ru = _plain(props.get("Short RU", {})) or short_en
        slug = _plain(props.get("Slug", {})) or _slugify(title_en)
        icon = None
        try:
            icon = (p.get("icon", {}) or {}).get("emoji")
        except Exception:
            pass
        tags_prop = props.get("Tags", {})
        tags_list: List[str] = []
        if tags_prop.get("type") == "multi_select":
            tags_list = [x.get("name", "") for x in tags_prop.get("multi_select", []) if x.get("name")]

        bullets_en = _rich_to_lines(props.get("Bullets EN", {})) or _rich_to_lines(props.get("Bullets", {}))
        bullets_ru = _rich_to_lines(props.get("Bullets RU", {}))
        examples_en = _rich_to_lines(props.get("Examples EN", {})) or _rich_to_lines(props.get("Examples", {}))
        examples_ru = _rich_to_lines(props.get("Examples RU", {}))

        items.append(
            {
                "slug": slug,
                "title_en": title_en,
                "title_ru": title_ru,
                "short_en": short_en,
                "short_ru": short_ru,
                "icon": icon,
                "tags": tags_list,
                "bullets_en": bullets_en,
                "bullets_ru": bullets_ru,
                "examples_en": examples_en,
                "examples_ru": examples_ru,
            }
        )

    # Deduplicate by slug
    by_slug: Dict[str, Dict[str, Any]] = {}
    for s in items:
        by_slug[s["slug"]] = s
    return list(by_slug.values())


def load_seed_skills(lang: str) -> List[Dict[str, Any]]:
    seeds_en = _read_seed("en")
    seeds_ru = _read_seed("ru")

    ru_by_slug: Dict[str, Dict[str, Any]] = {x.get("slug") or _slugify(x.get("title_en", "")): x for x in seeds_ru}
    merged_seeds: Dict[str, Dict[str, Any]] = {}
    for e in seeds_en:
        slug = e.get("slug") or _slugify(e.get("title_en", ""))
        r = ru_by_slug.get(slug, {})
        merged_seeds[slug] = {
            "slug": slug,
            "title_en": e.get("title_en", ""),
            "title_ru": r.get("title_ru") or e.get("title_ru") or e.get("title_en", ""),
            "short_en": e.get("short_en", ""),
            "short_ru": r.get("short_ru") or e.get("short_ru") or e.get("short_en", ""),
            "icon": e.get("icon") or r.get("icon"),
            "tags": e.get("tags") or r.get("tags") or [],
            "bullets_en": e.get("bullets_en") or [],
            "bullets_ru": r.get("bullets_ru") or e.get("bullets_ru") or [],
            "examples_en": e.get("examples_en") or [],
            "examples_ru": r.get("examples_ru") or e.get("examples_ru") or [],
        }

    # Project to requested language
    key = "ru" if lang == "ru" else "en"
    projected: List[Dict[str, Any]] = []
    for s in merged_seeds.values():
        projected.append(
            {
                "slug": s["slug"],
                "title": s["title_ru"] if key == "ru" else s["title_en"],
                "short": s["short_ru"] if key == "ru" else s["short_en"],
                "icon": s.get("icon"),
                "tags": s.get("tags", []),
                "bullets": s.get("bullets_ru", []) if key == "ru" else s.get("bullets_en", []),
                "examples": s.get("examples_ru", []) if key == "ru" else s.get("examples_en", []),
            }
        )
    return sorted(projected, key=lambda x: x["slug"])


def _map_item(x: Dict[str, Any], lang: str) -> Dict[str, Any]:
    def g(*keys: str, default: Any = "") -> Any:
        for k in keys:
            v = x.get(k)
            if v not in (None, ""):
                return v
        return default

    return {
        "slug": (g("slug", "Slug", "SLUG", default="").strip() or _slugify(g("Title EN", "Title", "Name", default=""))),
        "title": g("Title RU", "title_ru", default="") if lang == "ru" else g("Title EN", "title_en", "Title", default=""),
        "short": g("Short RU", "short_ru", default="") if lang == "ru" else g("Short EN", "short_en", "Short", default=""),
        "icon": g("icon", "Icon", "emoji", default=None) or None,
        "tags": g("Tags", "tags", default=[]) or [],
        "bullets": g("Bullets RU", "bullets_ru", default=[]) if lang == "ru" else g("Bullets EN", "bullets_en", default=[]),
        "examples": g("Examples RU", "examples_ru", default=[]) if lang == "ru" else g("Examples EN", "examples_en", default=[]),
    }


def load_skills(lang: str) -> List[Dict[str, Any]]:
    # normalize language
    lang = "ru" if (lang or "").lower().startswith("ru") else "en"

    token, db = notion_token(), skills_db()
    try:
        if token and db:
            data = _fetch_skills_from_notion(db_id=db, token=token, lang=lang, timeout=notion_timeout())
            # map properties defensively
            mapped = [_map_item(x, lang) for x in data if x]
            if mapped:
                return sorted(mapped, key=lambda i: i.get("slug", ""))
    except Exception as e:
        log.warning("Skills: Notion fetch failed (%s). Falling back to seeds.", e)

    return load_seed_skills(lang)


