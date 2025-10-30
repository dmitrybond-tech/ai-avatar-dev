# MiniApp API

Local dev:

```
# in apps/miniapp-api
python -m venv .venv
. .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn apps.miniapp_api.main:app --reload --host 127.0.0.1 --port 8080
```

Endpoints:
- GET `/healthz`
- GET `/rules`
- GET `/tasks/status`
- GET `/cal/link`
- POST `/api/chat/stub`

Notes:
- Responses use Pydantic models; stubs are easy to swap to Notion later.
