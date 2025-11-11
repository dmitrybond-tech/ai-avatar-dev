from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from apps.miniapp_api.core import env as env_utils
from apps.miniapp_api.integrations.notion_public import _client as notion_client, query_public_tasks
from apps.miniapp_api.routers import briefs as briefs_router
from apps.miniapp_api.routers.chat import router as chat_router
from apps.miniapp_api.routers.public_tasks import router as public_tasks_router
from apps.miniapp_api.routers.tasks import router as tasks_router
from apps.miniapp_api.routers.skills import (
    alias_router as legacy_skills_router,
    api_router as skills_api_router,
    router as skills_router,
)
from apps.miniapp_api.services.llm_provider import LLMProvider
from apps.miniapp_api.services.skills_service import SkillsRepository
from apps.miniapp_api.services.telegram_exporter import TelegramExporter


logger = logging.getLogger("miniapp_api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="Miniapp API",
    version="2.0.0",
    openapi_url="/api/openapi.json",
    docs_url=None,
    redoc_url=None,
)

skills_repo = SkillsRepository()
llm_provider = LLMProvider()
telegram_exporter = TelegramExporter()


def _parse_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS")
    if not raw:
        return [
            "https://miniapp.dmitrybond.tech",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return parsed or [
        "https://miniapp.dmitrybond.tech",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,
)


@app.on_event("startup")
async def on_startup() -> None:
    app.state.start_time = time.time()
    app.state.skills_repo = skills_repo
    app.state.llm_provider = llm_provider
    app.state.telegram_exporter = telegram_exporter
    app.state.tasks_state = "unknown"
    try:
        skills_repo.refresh()
    except Exception as exc:  # pragma: no cover - defensive load
        logger.warning("Failed to preload skills: %s", exc)
    try:
        snapshot = env_utils.notion_env_snapshot()
        logger.info(
            "notion_env token=%s skills_db=%s tasks_db=%s",
            snapshot["token"],
            snapshot["skills_db"],
            snapshot["tasks_db"],
        )
    except Exception as exc:  # pragma: no cover - defensive log
        logger.debug("Failed to log notion env snapshot: %s", exc)


@app.on_event("startup")
async def log_routes() -> None:
    try:
        paths = sorted({route.path for route in app.routes if isinstance(route, APIRoute)})
        logger.info("Registered routes: %s", paths)
    except Exception as exc:  # pragma: no cover - diagnostics only
        logger.debug("Failed to enumerate routes: %s", exc)


@app.get("/api/healthz", include_in_schema=False)
async def healthz() -> Dict[str, Any]:
    snapshot = skills_repo.snapshot()
    notion_snapshot = env_utils.notion_env_snapshot()
    tasks_state = getattr(app.state, "tasks_state", "unknown")
    status = "ok"
    if not snapshot.notion or tasks_state == "degraded":
        status = "degraded"
    return {
        "status": status,
        "skills_provider": snapshot.source or "unknown",
        "used_llm": llm_provider.available,
        "notion": {
            "token": notion_snapshot["token"],
            "skills_db": notion_snapshot["skills_db"],
            "tasks_db": notion_snapshot["tasks_db"],
            "tasks_state": tasks_state,
        },
        "timestamp": int(time.time()),
    }


@app.get("/api/healthz/revision", include_in_schema=False)
def healthz_revision() -> Dict[str, str]:
    revision = os.getenv("org.opencontainers.image.revision") or os.getenv("APP_REVISION") or "unknown"
    return {"revision": revision}


@app.get("/api/public/tasks", include_in_schema=False)
def alias_public_tasks(
    statuses: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> List[dict]:
    dbid = env_utils.tasks_db()
    if not dbid:
        return []
    try:
        client = notion_client()
    except Exception:
        return []
    parsed = None
    if statuses and statuses.strip():
        parsed = [item.strip() for item in statuses.split(",") if item.strip()]
    if not parsed:
        parsed = ["In Progress", "Review"]
    try:
        return query_public_tasks(client, dbid, parsed, limit)
    except Exception:
        return []


@app.get("/api/public", include_in_schema=False)
def alias_public_legacy(
    statuses: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> List[dict]:
    return alias_public_tasks(statuses=statuses, limit=limit)


app.include_router(chat_router)
app.include_router(tasks_router)
app.include_router(public_tasks_router, prefix="/api")
app.include_router(skills_router)
app.include_router(skills_api_router)
app.include_router(legacy_skills_router)
app.include_router(briefs_router.router, prefix="/api")
app.include_router(briefs_router.legacy_router)


if os.getenv("DEBUG_DIAG") == "1":
    @app.get("/diag/env", include_in_schema=False)
    def diag_env() -> Dict[str, Any]:
        snapshot = env_utils.notion_env_snapshot()
        return {
            "NOTION_TOKEN": snapshot["token"],
            "SKILLS_DB": snapshot["skills_db"],
            "TASKS_DB": snapshot["tasks_db"],
            "TIMEOUT": env_utils.notion_timeout(),
        }