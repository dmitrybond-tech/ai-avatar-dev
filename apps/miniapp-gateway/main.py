"""Miniapp Gateway - Notion-powered fuzzy matching API."""
import os
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from rapidfuzz import fuzz, process

load_dotenv()

app = FastAPI(title="Miniapp Gateway", version="0.1.0")

# CORS for Mini App frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
NOTION_SECRET = os.getenv("NOTION_SECRET")
NOTION_DB = os.getenv("NOTION_DB")
CAL_LINK = os.getenv("CAL_LINK", "https://cal.com")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "600"))

# In-memory cache
_cache: Dict[str, Any] = {"data": None, "timestamp": 0}


class ReplyRequest(BaseModel):
    """User query."""
    text: str


class ReplyResponse(BaseModel):
    """Structured answer from Notion DB."""
    verdict: str
    level: Optional[str] = None
    years: Optional[int] = None
    examples: Optional[str] = None
    cal_link: str


def fetch_notion_db() -> List[Dict[str, Any]]:
    """Fetch all pages from Notion DB."""
    if not NOTION_SECRET or not NOTION_DB:
        raise ValueError("NOTION_SECRET and NOTION_DB must be set")
    
    url = f"https://api.notion.com/v1/databases/{NOTION_DB}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_SECRET}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    all_results = []
    has_more = True
    start_cursor = None
    
    while has_more:
        body = {}
        if start_cursor:
            body["start_cursor"] = start_cursor
        
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        all_results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")
    
    return all_results


def extract_text(prop: Dict[str, Any]) -> str:
    """Extract plain text from Notion property."""
    prop_type = prop.get("type")
    if prop_type == "title":
        return "".join(rt.get("plain_text", "") for rt in prop.get("title", []))
    elif prop_type == "rich_text":
        return "".join(rt.get("plain_text", "") for rt in prop.get("rich_text", []))
    elif prop_type == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    elif prop_type == "number":
        num = prop.get("number")
        return str(int(num)) if num is not None else ""
    elif prop_type == "multi_select":
        return ", ".join(ms.get("name", "") for ms in prop.get("multi_select", []))
    return ""


def parse_notion_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Parse Notion pages into searchable records."""
    records = []
    for page in pages:
        props = page.get("properties", {})
        
        name = extract_text(props.get("name", {}))
        if not name:
            continue
        
        level = extract_text(props.get("level", {}))
        years = extract_text(props.get("years", {}))
        tags = extract_text(props.get("tags", {}))
        keywords = extract_text(props.get("keywords", {}))
        examples = extract_text(props.get("examples", {}))
        
        # Combine searchable fields
        search_text = f"{name} {tags} {keywords}".lower()
        
        records.append({
            "name": name,
            "level": level,
            "years": years,
            "tags": tags,
            "keywords": keywords,
            "examples": examples,
            "search_text": search_text,
        })
    
    return records


def get_cached_data() -> List[Dict[str, str]]:
    """Get cached Notion data or fetch fresh if expired."""
    now = time.time()
    if _cache["data"] is None or (now - _cache["timestamp"]) > CACHE_TTL:
        pages = fetch_notion_db()
        _cache["data"] = parse_notion_pages(pages)
        _cache["timestamp"] = now
    return _cache["data"]


def fuzzy_match(query: str, records: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Find best matching record using fuzzy search."""
    if not records:
        return None
    
    query_lower = query.lower()
    
    # Extract search texts for fuzzy matching
    choices = [(rec["search_text"], i) for i, rec in enumerate(records)]
    
    # Use rapidfuzz to find best match
    result = process.extractOne(
        query_lower,
        choices,
        scorer=fuzz.token_set_ratio,
        score_cutoff=50  # Minimum 50% match
    )
    
    if not result:
        return None
    
    _, score, idx = result
    return records[idx]


@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"ok": True}


@app.post("/reply", response_model=ReplyResponse)
async def reply(req: ReplyRequest):
    """
    Process user query and return fuzzy-matched answer from Notion DB.
    
    Returns structured response with skill details and booking link.
    """
    try:
        records = get_cached_data()
        
        if not records:
            return ReplyResponse(
                verdict="I don't have any skills configured yet. Please check back later!",
                cal_link=CAL_LINK
            )
        
        match = fuzzy_match(req.text, records)
        
        if not match:
            return ReplyResponse(
                verdict=f"I couldn't find a match for '{req.text}'. Try asking about specific technologies or skills!",
                cal_link=CAL_LINK
            )
        
        # Build verdict message
        verdict_parts = [f"I can help with {match['name']}!"]
        if match["level"]:
            verdict_parts.append(f"Level: {match['level']}")
        if match["years"]:
            verdict_parts.append(f"Experience: {match['years']} years")
        
        verdict = " • ".join(verdict_parts)
        
        return ReplyResponse(
            verdict=verdict,
            level=match["level"] or None,
            years=int(match["years"]) if match["years"] else None,
            examples=match["examples"] or None,
            cal_link=CAL_LINK
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/refresh")
async def refresh():
    """
    Force refresh Notion DB cache.
    
    Returns the count of refreshed records.
    """
    try:
        pages = fetch_notion_db()
        _cache["data"] = parse_notion_pages(pages)
        _cache["timestamp"] = time.time()
        
        return {
            "ok": True,
            "count": len(_cache["data"]),
            "message": f"Refreshed {len(_cache['data'])} skills from Notion"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("GATEWAY_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)

