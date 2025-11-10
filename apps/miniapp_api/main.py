import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from apps.miniapp_api.core import env as env_utils
from apps.miniapp_api.models.chat import init_db
from apps.miniapp_api.routers import chat as chat_router_module
from apps.miniapp_api.routers import skills as skills_router

logger = logging.getLogger("miniapp_api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="Miniapp API",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url=None,
    redoc_url=None,
)

app.state.skills_config_error = None

# CORS for local dev
allowed_origins = [
    "https://miniapp.dmitrybond.tech",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers after app is created
try:
    from apps.miniapp_api.routers.public_tasks import router as public_tasks_router

    app.include_router(public_tasks_router, prefix="/api")
except Exception:
    logging.getLogger(__name__).exception("Failed to include public_tasks router")

try:
    from apps.miniapp_api.routers import briefs as briefs_router

    app.include_router(briefs_router.router, prefix="/api")
except Exception:
    logging.getLogger(__name__).exception("Failed to include briefs router")


@app.get("/api/healthz", include_in_schema=False)
async def healthz_api() -> dict:
    notion_token = bool(env_utils.notion_token())
    notion_skills = bool(env_utils.skills_db())
    notion_tasks = bool(env_utils.tasks_db())
    missing = []
    if not notion_token:
        missing.append("NOTION_API_KEY")
    if not notion_skills:
        missing.append("NOTION_DB_SKILLS")
    if not notion_tasks:
        missing.append("NOTION_PUBLIC_TASKS_DB_ID")

    if missing:
        return {
            "ok": True,
            "status": "degraded",
            "notion": {"status": "unreachable", "missing": missing},
        }
    return {"ok": True, "status": "ok"}


@app.get("/api/healthz/revision", include_in_schema=False)
def healthz_revision_api() -> dict:
    revision = os.getenv("org.opencontainers.image.revision") or os.getenv("APP_REVISION") or "unknown"
    return {"revision": revision}


@app.on_event("startup")
async def init_chat_storage() -> None:
    try:
        init_db()
    except Exception:  # noqa: BLE001
        logger.exception("Chat database init failed")


@app.on_event("startup")
async def log_routes() -> None:
    try:
        route_paths = sorted([r.path for r in app.routes if isinstance(r, APIRoute)])
        logger.info("Registered routes (miniapp_api): %s", route_paths)
    except Exception as e:
        logger.debug("Failed to list routes: %s", e.__class__.__name__)


@app.on_event("startup")
async def log_notion_env_snapshot() -> None:
    try:
        token = env_utils.notion_token()
        skills_db = env_utils.skills_db()
        tasks_db = env_utils.tasks_db()
        logger.info(
            "NOTION_API_KEY=%s; NOTION_DB_SKILLS=%s; NOTION_PUBLIC_TASKS_DB_ID=%s",
            f"SET(len:{len(token)})" if token else "EMPTY",
            "SET" if skills_db else "EMPTY",
            "SET" if tasks_db else "EMPTY",
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to log notion env snapshot: %s", exc.__class__.__name__)


@app.on_event("startup")
async def validate_skills_config() -> None:
    try:
        from apps.miniapp_api.core.settings import SettingsError, get_settings

        settings = get_settings()
        try:
            settings.ensure_skills_config()
            app.state.skills_config_error = None
        except SettingsError as exc:
            app.state.skills_config_error = str(exc)
            logger.error("Skills configuration missing: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error while validating skills settings: %s", exc)

app.include_router(skills_router, prefix="/api")
app.include_router(chat_router_module.router, prefix="/api")


# Optional diagnostics endpoint guarded by DEBUG_DIAG=1
try:
    if os.getenv("DEBUG_DIAG") == "1":
        @app.get("/diag/env")
        def diag_env() -> dict:
            from apps.miniapp_api.core import env as _env
            t = _env.notion_token()
            return {
                "NOTION_TOKEN": "SET" if bool(t) else "EMPTY",
                "SKILLS_DB": bool(_env.skills_db()),
                "TASKS_DB": bool(_env.tasks_db()),
                "TIMEOUT": _env.notion_timeout(),
            }
except Exception:
    pass


@app.post("/api/ask", include_in_schema=False)
async def ask_alias(payload: chat_router_module.AskRequest) -> chat_router_module.AskResponse:
    return await chat_router_module.ask(payload)


@app.post("/api/export/telegram", include_in_schema=False)
async def export_alias(payload: chat_router_module.ExportRequest) -> chat_router_module.ExportResponse:
    return await chat_router_module.export_chat(payload)

# Public tasks aliases (/api/public and /public) returning same payload as /api/tasks/public
try:
    from fastapi import HTTPException, Query
    from typing import List, Optional

    from apps.miniapp_api.integrations.notion_public import (
        _client as _notion_client,
        query_public_tasks as _query_public_tasks,
    )

    def _parse_statuses(statuses: Optional[str]) -> Optional[List[str]]:
        if statuses and statuses.strip():
            parsed = [s.strip() for s in statuses.split(",") if s.strip()]
            return parsed or None
        return None

    def _resolve_dbid() -> str:
        dbid = env_utils.tasks_db()
        if not dbid:
            raise HTTPException(status_code=502, detail={"error": "notion_unreachable"})
        return dbid

    @app.get("/api/public")
    def api_public(statuses: Optional[str] = Query(default=None), limit: int = Query(default=20, ge=1, le=50)) -> List[dict]:
        dbid = _resolve_dbid()
        sts = _parse_statuses(statuses) or ["In Progress", "Review"]
        client = _notion_client()
        return _query_public_tasks(client, dbid, sts, limit)
except Exception:
    logging.getLogger(__name__).exception("Failed to register public tasks aliases")

