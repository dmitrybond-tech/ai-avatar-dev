from __future__ import annotations

import os
from typing import List, Optional, Tuple

from notion_client import Client, APIResponseError


# Environment variables
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
NOTION_TIMEOUT = int(os.getenv("NOTION_TIMEOUT", "10"))


def _client() -> Client:
    """Create and return a Notion client instance using env vars."""
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY is not set")
    return Client(auth=NOTION_API_KEY, timeout_ms=NOTION_TIMEOUT * 1000)


def resolve_schema(client: Client, dbid: str) -> dict:
    """Return schema details: title_prop, public_prop, status_prop, status_values."""
    db = client.databases.retrieve(database_id=dbid)
    props = db.get("properties", {})

    title_prop = None
    for prop_name, prop_data in props.items():
        if prop_data.get("type") == "title":
            title_prop = prop_name
            break
    if not title_prop:
        raise ValueError("No title property found")

    public_prop = None
    for prop_name, prop_data in props.items():
        if prop_data.get("type") == "checkbox" and "public" in prop_name.lower():
            public_prop = prop_name
            break
    if not public_prop:
        for prop_name, prop_data in props.items():
            if prop_data.get("type") == "checkbox":
                public_prop = prop_name
                break
    if not public_prop:
        raise ValueError("No public checkbox property found")

    status_prop = None
    status_type = None
    status_values: List[str] = []
    for prop_name, prop_data in props.items():
        t = prop_data.get("type")
        if t == "status":
            status_prop = prop_name
            status_type = "status"
            status_values = [o.get("name", "") for o in prop_data.get("status", {}).get("options", []) if o.get("name")]
            break
        if t == "select" and status_prop is None:
            status_prop = prop_name
            status_type = "select"
            status_values = [o.get("name", "") for o in prop_data.get("select", {}).get("options", []) if o.get("name")]
    if not status_prop:
        raise ValueError("No status/select property found")

    return {
        "title_prop": title_prop,
        "public_prop": public_prop,
        "status_prop": status_prop,
        "status_type": status_type,
        "status_values": status_values,
    }


def _match_statuses(requested: Optional[List[str]], available: List[str]) -> List[str]:
    if not requested:
        return []
    m = {s.strip().lower(): s for s in available}
    out: List[str] = []
    for r in requested:
        key = r.strip().lower()
        if key in m:
            out.append(m[key])
    return out


def query_public_tasks(client: Client, dbid: str, statuses: Optional[List[str]], limit: int) -> List[dict]:
    """
    Query public tasks and map to a thin DTO.

    Returns items with: id, title, status, lastEdited, url, optional progress (number) and scope (string).
    """
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")

    schema = resolve_schema(client, dbid)

    filters = [{"property": schema["public_prop"], "checkbox": {"equals": True}}]
    matched = _match_statuses(statuses, schema["status_values"]) if statuses else []
    if matched:
        conds = []
        for s in matched:
            if schema["status_type"] == "status":
                conds.append({"property": schema["status_prop"], "status": {"equals": s}})
            else:
                conds.append({"property": schema["status_prop"], "select": {"equals": s}})
        filters.append({"or": conds}) if len(conds) > 1 else filters.append(conds[0])

    query_filter = {"and": filters} if len(filters) > 1 else filters[0]

    results: List[dict] = []
    has_more, cursor = True, None
    while has_more and len(results) < limit:
        params = {
            "database_id": dbid,
            "filter": query_filter,
            "page_size": min(100, limit - len(results)),
            "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        }
        if cursor:
            params["start_cursor"] = cursor
        resp = client.databases.query(**params)
        results.extend(resp.get("results", []))
        has_more = resp.get("has_more", False)
        cursor = resp.get("next_cursor")

    items: List[dict] = []
    for page in results[:limit]:
        props = page.get("properties", {})
        page_id = page.get("id", "")

        # title
        title_arr = props.get(schema["title_prop"], {}).get("title", [])
        title = "".join(rt.get("plain_text", "") for rt in title_arr) or "Untitled"

        # status
        sp = props.get(schema["status_prop"], {})
        if schema["status_type"] == "status":
            status = (sp.get("status") or {}).get("name") or ""
        else:
            status = (sp.get("select") or {}).get("name") or ""

        # optional progress: try number or formula (number)
        progress = None
        scope_text = None
        for pname, pdata in props.items():
            ptype = pdata.get("type")
            if progress is None and ptype == "number" and "progress" in pname.lower():
                progress = pdata.get("number")
            elif progress is None and ptype == "formula":
                if (pdata.get("formula") or {}).get("type") == "number":
                    progress = (pdata.get("formula") or {}).get("number")
            if scope_text is None and ptype == "rich_text" and ("summary" in pname.lower() or "scope" in pname.lower()):
                rts = pdata.get("rich_text", [])
                scope_text = "".join(rt.get("plain_text", "") for rt in rts).strip() or None

        items.append({
            "id": page_id,
            "title": title,
            "status": status,
            "lastEdited": page.get("last_edited_time", ""),
            "url": f"https://notion.so/{page_id.replace('-', '')}",
            **({"progress": int(progress)} if isinstance(progress, (int, float)) else {}),
            **({"scope": scope_text} if scope_text else {}),
        })

    return items

