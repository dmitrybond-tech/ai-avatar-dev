import os
from typing import Any, Dict, List, Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ru")
CAL_USERNAME = os.getenv("CAL_USERNAME", "dmitrybond")
CAL_HOST = os.getenv("CAL_HOST", "cal.com")

app = FastAPI(title="MiniApp API", version="1.0.0")
# CORS left in place for local dev convenience; same-origin in prod avoids CORS usage
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

try:
    # Mount public tasks router under /api prefix
    from apps.miniapp_api.routers.public_tasks import router as public_tasks_router
    app.include_router(public_tasks_router, prefix="/api")
except Exception:
    # Optional in dev if dependencies are missing; avoids startup crash
    pass


class SkillItem(BaseModel):
    id: str
    title: str
    desc: str | None = None
    tags: List[str] | None = None


class RulesResponse(BaseModel):
    items: List[SkillItem] = Field(default_factory=list)


class TaskItem(BaseModel):
    id: str
    title: str
    status: Literal["todo", "in_progress", "done"]
    updatedAt: str


class TasksStatusResponse(BaseModel):
    items: List[TaskItem] = Field(default_factory=list)


class ChatIn(BaseModel):
    text: str


class ChatOut(BaseModel):
    reply: str


class CalLinkResponse(BaseModel):
    url: str


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/rules", response_model=RulesResponse)
async def get_rules() -> RulesResponse:
    return RulesResponse(items=[
        SkillItem(id="cloud", title="Cloud migrations", desc="AWS/Azure/GCP", tags=["cloud", "migration"]),
        SkillItem(id="pm", title="Project/Release mgmt", tags=["pmi", "agile"]),
        SkillItem(id="integrations", title="Systems integrations", desc="APIs, webhooks, ETL"),
        SkillItem(id="devops", title="DevOps & CI/CD", tags=["docker", "k8s", "gh-actions"]),
        SkillItem(id="ai", title="AI assistants", desc="RAG, LLM tools, ChatOps"),
        SkillItem(id="security", title="Security reviews", tags=["policies", "hardening"]),
        SkillItem(id="product", title="Product discovery", tags=["MVP", "roadmap"]),
        SkillItem(id="automation", title="Workflow automation", tags=["zapier", "n8n", "make"]),
    ])


@app.get("/tasks/status", response_model=TasksStatusResponse)
async def tasks_status() -> TasksStatusResponse:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    return TasksStatusResponse(items=[
        TaskItem(id="t-1", title="Client onboarding", status="in_progress", updatedAt=now),
        TaskItem(id="t-2", title="Infra audit", status="todo", updatedAt=now),
        TaskItem(id="t-3", title="MiniApp MVP", status="done", updatedAt=now),
    ])


@app.post("/api/chat/stub", response_model=ChatOut)
async def chat_stub(m: ChatIn) -> ChatOut:
    return ChatOut(reply="Понял. Могу помочь: 1) записать на встречу, 2) рассказать, что умею (skills), 3) уточнить ваш запрос.")


@app.get("/cal/link", response_model=CalLinkResponse)
async def cal_link() -> CalLinkResponse:
    return CalLinkResponse(url=f"https://{CAL_HOST}/{CAL_USERNAME}/intro-30m")


@app.get("/cal/suggest")
async def cal_suggest(event: str = Query(default="intro-30m"), lang: str = Query(default=DEFAULT_LANG)) -> Dict[str, Any]:
    username = os.getenv("CAL_USERNAME", CAL_USERNAME)
    host = os.getenv("CAL_HOST", CAL_HOST)
    url = f"https://{host}/{username}/{event}"
    cta = {
        "ru": "Забронировать встречу",
        "en": "Book a call",
    }
    return {
        "event": event,
        "lang": lang,
        "cta": cta.get(lang, cta[DEFAULT_LANG]),
        "url": url,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("apps.miniapp_api.main:app", host="0.0.0.0", port=port, reload=True)
