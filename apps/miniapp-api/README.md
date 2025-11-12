# MiniApp API

Local dev:

```
# in apps/miniapp-api
python -m venv .venv
. .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn apps.miniapp_api.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints:
- GET `/healthz` and `/api/healthz`
- GET `/skills` and `/api/skills?lang=ru|en` — list skills from CSV
- GET `/api/skills/{slug}?lang=ru|en` — get skill detail
- GET `/api/skills/debug` — diagnostics
- POST `/api/skills/ask` — ask about skills using Grok
- POST `/api/chat/ask_grok` — FatContext Grok endpoint (optional, falls back to `/api/skills/ask`)
- GET `/tasks/status`
- GET `/cal/link`
- POST `/api/chat/stub`

Notes:
- CSV is the active source when `SKILLS_SOURCE=csv` (set via `miniapp.csv.override.yml`).
- Skills CSV headers: `Title EN`, `Bullets EN`, `Bullets RU`, `Examples EN`, `Examples RU`, `Short EN`, `Short RU`, `Slug`, `Tags`, `Title RU`.
- The chat toggle ("Smart answer (LLM)") is only on the main chat screen, not on the Skills page.
