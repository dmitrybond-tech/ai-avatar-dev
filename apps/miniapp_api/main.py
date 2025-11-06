import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="MiniApp API", version="1.0.0")

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
    pass


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.get("/healthz/revision")
def healthz_revision() -> dict:
    revision = os.getenv("org.opencontainers.image.revision") or os.getenv("APP_REVISION") or "unknown"
    return {"revision": revision}

