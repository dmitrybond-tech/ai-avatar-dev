import os

from fastapi import FastAPI

from apps.miniapp_api.routers.public_tasks import router as public_tasks_router


app = FastAPI(title="MiniApp API", version="1.0.0")

app.include_router(public_tasks_router, prefix="/api", tags=["public-tasks"])


# Expose image revision for quick verification
@app.get("/healthz/revision")
def healthz_revision() -> dict:
    revision = os.getenv("APP_REVISION") or "unknown"
    return {"revision": revision}

