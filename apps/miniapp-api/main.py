from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .routers.chat_v2 import router as chat_router
from .routers.public_tasks import router as public_tasks_router
from .routers.skills import alias_router as skills_alias_router, router as skills_router
from .routers.briefs import router as briefs_router
from .services.llm import LLMProvider
from .services.skills import SkillsRepository
from .services.telegram import TelegramExporter

logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="MiniApp API", version="2.0.0")

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

skills_repo = SkillsRepository()
llm_provider = LLMProvider()
telegram_exporter = TelegramExporter()


@app.on_event("startup")
async def on_startup() -> None:
    app.state.start_time = time.time()
    app.state.skills_repo = skills_repo
    app.state.llm_provider = llm_provider
    app.state.telegram_exporter = telegram_exporter
    try:
        skills_repo.refresh()
    except Exception as exc:  # pragma: no cover - defensive load
        logger.warning("Failed to preload skills: %s", exc)


app.include_router(public_tasks_router, prefix="/api")
app.include_router(skills_router)
app.include_router(skills_router, prefix="/api")
app.include_router(skills_alias_router)
app.include_router(briefs_router)
app.include_router(briefs_router, prefix="/api")
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
    revision = os.getenv("org.opencontainers.image.revision") or os.getenv("APP_REVISION") or "unknown"
    return {"revision": revision}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks/status", response_model=TasksStatusResponse)
async def tasks_status() -> TasksStatusResponse:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    return TasksStatusResponse(
        items=[
            TaskItem(id="t-1", title="Client onboarding", status="in_progress", updatedAt=now),
            TaskItem(id="t-2", title="Infra audit", status="todo", updatedAt=now),
            TaskItem(id="t-3", title="MiniApp MVP", status="done", updatedAt=now),
        ]
    )


@app.get("/cal/link", response_model=CalLinkResponse)
async def cal_link() -> CalLinkResponse:
    host = os.getenv("CAL_HOST", "cal.com")
    username = os.getenv("CAL_USERNAME", "dmitrybond")
    return CalLinkResponse(url=f"https://{host}/{username}/intro-30m")


@app.get("/cal/suggest")
async def cal_suggest(event: str = Query(default="intro-30m"), lang: str = Query(default=None)) -> Dict[str, Any]:
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


if __name__ != "__main__":  # pragma: no cover - helpful logs for container starts
    try:
        paths = sorted({route.path for route in app.routes})
        logger.info("Registered routes: %s", paths)
    except Exception:
        pass

