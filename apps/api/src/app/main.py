"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.settings import settings
from app.core.logging import setup_logging, get_logger
from app.db.connection import init_db, close_db
from app.adapters.web import health, chat, chat_ws, voice, telegram, chat_stub
from app.adapters.web import client_log, public_tasks
from app.integrations.notion_public_tasks import assert_schema

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting API server...")
    await init_db()
    
    # Ensure TTS data directory exists
    tts_dir = Path("/data/tts")
    tts_dir.mkdir(parents=True, exist_ok=True)
    
    # Assert Notion schema if configured
    try:
        if settings.notion_api_key and settings.notion_public_tasks_db_id:
            assert_schema()
            logger.info("Notion schema validation passed")
        else:
            logger.info("Notion integration not configured (missing API key or DB ID)")
    except Exception as e:
        logger.warning(f"Notion schema validation failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API server...")
    await close_db()


app = FastAPI(
    title="AI Avatar API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
cors_origins = [settings.website_origin, "https://web.telegram.org"]

# Optional: Allow dev CORS (set ALLOW_DEV_CORS=1 for local development)
import os
if os.getenv("ALLOW_DEV_CORS") == "1":
    cors_origins.append("*")
    logger.warning("Dev CORS enabled - allowing all origins")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for TTS output
app.mount("/static/tts", StaticFiles(directory="/data/tts"), name="tts")

# Register routers
app.include_router(health.router, tags=["health"])
app.include_router(chat.router, tags=["chat"])
app.include_router(chat_ws.router, tags=["chat"])
app.include_router(voice.router, tags=["voice"])
app.include_router(telegram.router, tags=["telegram"])
app.include_router(chat_stub.router, tags=["chat-stub"])
app.include_router(client_log.router, tags=["client-log"])
app.include_router(public_tasks.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )

