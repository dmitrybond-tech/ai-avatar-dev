import os
from typing import Any, Dict, List, Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="MiniApp API", version="1.0.0")

DEFAULT_ORIGINS = [
    "https://miniapp.dmitrybond.tech",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def _parse_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS")
    if not raw:
        return DEFAULT_ORIGINS
    parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return parsed or DEFAULT_ORIGINS


allowed_origins = _parse_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,
)

# Mount public tasks router under /api prefix
# Use relative import to survive dash/underscore copy
from .routers.public_tasks import router as public_tasks_router
from .routers.skills import router as skills_router
from .routers.briefs import router as briefs_router
try:
    from .app.routers.chat import router as chat_router  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - defensive import for packaging quirks
    chat_router = None
app.include_router(public_tasks_router, prefix="/api")
app.include_router(skills_router)
app.include_router(skills_router, prefix="/api")
app.include_router(briefs_router)
app.include_router(briefs_router, prefix="/api")
if chat_router is not None:
    app.include_router(chat_router)


class TaskItem(BaseModel):
    id: str
    title: str
    status: Literal["todo", "in_progress", "done"]
    updatedAt: str


class TasksStatusResponse(BaseModel):
    items: List[TaskItem] = Field(default_factory=list)


class CalLinkResponse(BaseModel):
    url: str


@app.get("/healthz")
async def healthz() -> Dict[str, bool]:
    return {"ok": True}


@app.get("/healthz/revision")
def healthz_revision() -> Dict[str, str]:
    """Return container image revision for deployment verification."""
    # Try Docker image label first, then APP_REVISION env var
    revision = os.getenv("org.opencontainers.image.revision") or os.getenv("APP_REVISION") or "unknown"
    return {"revision": revision}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


 


@app.get("/tasks/status", response_model=TasksStatusResponse)
async def tasks_status() -> TasksStatusResponse:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    return TasksStatusResponse(items=[
        TaskItem(id="t-1", title="Client onboarding", status="in_progress", updatedAt=now),
        TaskItem(id="t-2", title="Infra audit", status="todo", updatedAt=now),
        TaskItem(id="t-3", title="MiniApp MVP", status="done", updatedAt=now),
    ])


@app.get("/cal/link", response_model=CalLinkResponse)
async def cal_link() -> CalLinkResponse:
    import os
    host = os.getenv("CAL_HOST", "cal.com")
    username = os.getenv("CAL_USERNAME", "dmitrybond")
    return CalLinkResponse(url=f"https://{host}/{username}/intro-30m")


@app.get("/cal/suggest")
async def cal_suggest(event: str = Query(default="intro-30m"), lang: str = Query(default=None)) -> Dict[str, Any]:
    import os
    default_lang = os.getenv("DEFAULT_LANG", "ru")
    if lang is None:
        lang = default_lang
    username = os.getenv("CAL_USERNAME", "dmitrybond")
    host = os.getenv("CAL_HOST", "cal.com")
    url = f"https://{host}/{username}/{event}"
    cta = {
        "ru": "Забронировать встречу",
        "en": "Book a call",
    }
    return {
        "event": event,
        "lang": lang,
        "cta": cta.get(lang, cta[default_lang]),
        "url": url,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("apps.miniapp_api.main:app", host="0.0.0.0", port=port, reload=True)

# Debug: print routes at container start (for verification)
# This runs when uvicorn imports the module (not in __main__ mode)
if __name__ != "__main__":
    import sys
    import logging
    logger = logging.getLogger(__name__)
    try:
        routes = sorted([r.path for r in app.routes])
        logger.info(f"Registered routes: {routes}")
    except Exception:
        pass  # Don't fail if routes aren't initialized yet
