import os
from typing import Any, Dict

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yaml

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
RULES_PATH = os.path.join(ROOT_DIR, "miniapp-api", "rules.yaml") if not os.path.exists(os.path.join(APP_DIR, "rules.yaml")) else os.path.join(APP_DIR, "rules.yaml")

DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ru")
CAL_USERNAME = os.getenv("CAL_USERNAME", "dmitrybond")
CAL_HOST = os.getenv("CAL_HOST", "cal.com")

app = FastAPI(title="MiniApp API", version="1.0.0")
# CORS configuration for production and local development
allowed_origins = [
    "https://miniapp.dmitrybond.tech",  # Production domain
    "http://localhost:5173",  # Local dev
    "http://127.0.0.1:5173",  # Local dev alternative
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,  # Set to False for security
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def load_rules() -> Dict[str, Any]:
    path = RULES_PATH
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/rules")
async def get_rules(lang: str | None = Query(default=None)) -> Dict[str, Any]:
    rules = load_rules()
    # Optionally trim copy to single language if specified
    if lang:
        selected_lang = lang if lang in rules.get("languages", []) else DEFAULT_LANG
        # Make a language-specific projection without mutating source
        def project_text(node: Any) -> Any:
            if isinstance(node, dict):
                if set(node.keys()) >= {"ru", "en"}:
                    return node.get(selected_lang, next(iter(node.values())))
                return {k: project_text(v) for k, v in node.items()}
            if isinstance(node, list):
                return [project_text(v) for v in node]
            return node
        projected = {
            "version": rules.get("version"),
            "language": selected_lang,
            "labels": project_text(rules.get("labels", {})),
            "intents": rules.get("intents", []),
            "scenes": project_text(rules.get("scenes", {})),
        }
        return projected
    return rules


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
    uvicorn.run("apps.miniapp_api.main:app", host="127.0.0.1", port=port, reload=True)
