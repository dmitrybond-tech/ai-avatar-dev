from fastapi import FastAPI

from apps.miniapp_api.routers.public_tasks import router as public_tasks_router


app = FastAPI(title="MiniApp API", version="1.0.0")

app.include_router(public_tasks_router, prefix="/api", tags=["public-tasks"])


