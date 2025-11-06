import os
import logging
from fastapi import FastAPI, APIRouter
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Miniapp API", version="1.0.0")

logger = logging.getLogger("miniapp_api")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

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
except Exception as e:
    logging.getLogger(__name__).warning("Failed to include public_tasks router: %s", e.__class__.__name__)


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.get("/healthz/revision")
def healthz_revision() -> dict:
    revision = os.getenv("org.opencontainers.image.revision") or os.getenv("APP_REVISION") or "unknown"
    return {"revision": revision}


@app.on_event("startup")
async def log_routes() -> None:
    try:
        route_paths = sorted([r.path for r in app.routes if isinstance(r, APIRoute)])
        logger.info("Registered routes (miniapp_api): %s", route_paths)
    except Exception as e:
        logger.debug("Failed to list routes: %s", e.__class__.__name__)

# /api prefix and flat paths for compatibility
try:
    from apps.miniapp_api.routers import skills as skills_router

    api = APIRouter(prefix="/api")
    api.include_router(skills_router.router, tags=["skills"]) 
    app.include_router(api)

    app.include_router(skills_router.router, tags=["skills-compat"]) 
except Exception as e:
    logging.getLogger(__name__).warning("Failed to include skills router: %s", e.__class__.__name__)

# Public tasks aliases (/api/public and /public) returning same payload as /api/tasks/public
try:
    from fastapi import Query, HTTPException
    from typing import List, Optional
    import os as _os
    from apps.miniapp_api.integrations.notion_public import _client as _notion_client, query_public_tasks as _query_public_tasks

    def _parse_statuses(statuses: Optional[str]) -> Optional[List[str]]:
        if statuses and statuses.strip():
            parsed = [s.strip() for s in statuses.split(",") if s.strip()]
            return parsed or None
        return None

    def _resolve_dbid() -> str:
        dbid = (_os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "") or _os.getenv("NOTION_DB", "")).strip()
        if not dbid:
            raise HTTPException(status_code=502, detail={"error": "notion_unreachable"})
        return dbid

    @app.get("/api/public")
    def api_public(statuses: Optional[str] = Query(default=None), limit: int = Query(default=20, ge=1, le=50)) -> List[dict]:
        dbid = _resolve_dbid()
        sts = _parse_statuses(statuses) or ["In Progress", "Review"]
        client = _notion_client()
        return _query_public_tasks(client, dbid, sts, limit)

    @app.get("/public")
    def public(statuses: Optional[str] = Query(default=None), limit: int = Query(default=20, ge=1, le=50)) -> List[dict]:
        dbid = _resolve_dbid()
        sts = _parse_statuses(statuses) or ["In Progress", "Review"]
        client = _notion_client()
        return _query_public_tasks(client, dbid, sts, limit)
except Exception as e:
    logging.getLogger(__name__).warning("Failed to register public tasks aliases: %s", e.__class__.__name__)

