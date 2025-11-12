from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .core import env as env_utils
from .routers.chat_v2 import router as chat_router
from .routers.public_tasks import router as public_tasks_router
from .routers.skills import api_router as skills_api_router, alias_router as skills_alias_router, router as skills_router
from .routers.briefs import router as briefs_router
from .routers.tasks import router as tasks_router
from .services.llm import LLMProvider
from .services.skills import SkillsRepository
from .services.telegram import TelegramExporter

logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="MiniApp API",
    version="2.0.0",
    openapi_url="/api/openapi.json",
    docs_url=None,
    redoc_url=None,
)

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
    app.state.tasks_state = "unknown"
    try:
        skills_repo.refresh()
    except Exception as exc:  # pragma: no cover - defensive load
        logger.warning("Failed to preload skills: %s", exc)
    try:
        snapshot = env_utils.snapshot()
        logger.info(
            "notion_env token=%s skills_db=%s tasks_db=%s",
            snapshot["token"],
            snapshot["skills_db"],
            snapshot["tasks_db"],
        )
    except Exception as exc:  # pragma: no cover - defensive log
        logger.debug("Failed to log notion env snapshot: %s", exc)


app.include_router(chat_router)
app.include_router(tasks_router)
app.include_router(public_tasks_router, prefix="/api")
app.include_router(skills_router)
app.include_router(skills_api_router)
app.include_router(skills_alias_router)
app.include_router(briefs_router)
app.include_router(briefs_router, prefix="/api")


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


@app.get("/openapi.json", include_in_schema=False)
async def legacy_openapi() -> Dict[str, Any]:
    return app.openapi()


@app.get("/api/cal/link", response_model=CalLinkResponse)
async def cal_link() -> CalLinkResponse:
    host = os.getenv("CAL_HOST", "cal.com")
    username = os.getenv("CAL_USERNAME", "dmitrybond")
    return CalLinkResponse(url=f"https://{host}/{username}/intro-30m")


@app.get("/api/cal/suggest")
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


# --- NVP: Simple chat (REST) ---
class ChatTurn(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class ChatRequest(BaseModel):
    lang: str = "ru"
    history: List[ChatTurn] = []
    message: str


class ChatResponse(BaseModel):
    reply: str
    usage: Dict[str, Any] = {}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> Dict[str, Any]:
    msg = (req.message or "").strip()
    base = "Понял. Давайте начнём. " if req.lang == "ru" else "Got it. Let's start. "
    return {"reply": base + msg, "usage": {"provider": "stub", "tokens": 0}}


# --- NVP: Streaming chat (SSE) ---
def _sse_event(event: str, data: Dict[str, Any]) -> str:
    # Server-Sent Events framing
    import json
    return "event: " + event + "\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


@app.get("/chat/stream")
async def chat_stream(request: Request, text: str, lang: str = "ru"):
    async def gen():
        # start
        yield _sse_event("start", {"ok": True})
        reply = (("Хм… " if lang == "ru" else "Hmm… ") + text).strip()
        # naive tokenization
        import asyncio
        for token in reply.split():
            if await request.is_disconnected():
                break
            yield _sse_event("token", {"t": token + " "})
            # tiny delay to emulate streaming
            await asyncio.sleep(0.03)
        yield _sse_event("end", {"ok": True})
    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("apps.miniapp_api.main:app", host="0.0.0.0", port=port, reload=True)


if __name__ != "__main__":  # pragma: no cover - helpful logs for container starts
    try:
        paths = sorted({route.path for route in app.routes})
        logger.info("Registered routes: %s", paths)
    except Exception:
        pass

