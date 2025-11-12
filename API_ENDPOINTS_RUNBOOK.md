# API Endpoints Runbook

## Overview
This runbook documents the API endpoint changes and verification steps for the skills and chat API migration to `/api` prefix.

## Changes Summary

### Backend (`apps/miniapp-api/main.py`)
- Created `APIRouter` with `/api` prefix
- Moved endpoints under `/api`:
  - `/api/healthz` (health check)
  - `/api/cal/link` and `/api/cal/suggest` (calendar endpoints)
  - `/api/chat` (REST chat endpoint)
  - `/api/chat/stream` (SSE streaming chat endpoint)
- `/api/skills` already existed via `skills_api_router`
- Added `/api/skills/search` endpoint for skill search

### Frontend (`apps/miniapp-web`)
- Created `apps/miniapp-web/src/shared/api.ts` with `API_BASE` and `apiUrl()` helpers
- Updated all skills endpoints to use `apiUrl("/skills...")`
- Updated chat endpoints to use `apiUrl("/chat")` and `apiUrl("/chat/stream")`
- All endpoints now consistently use `${VITE_API_BASE_URL}` (defaults to `/api`)

## Verification Commands

### Local Testing

```powershell
# Health check (local)
curl -i http://127.0.0.1:18080/api/healthz

# Skills endpoint (local)
curl -sS "http://127.0.0.1:18080/api/skills?lang=ru" | ConvertFrom-Json | Select-Object -First 3

# Chat REST endpoint (local)
curl -i -X POST http://127.0.0.1:18080/api/chat `
  -H "Content-Type: application/json" `
  -d '{\"lang\":\"ru\",\"history\":[],\"message\":\"проверка\"}'

# Chat SSE endpoint (local) - Note: PowerShell may not handle SSE well, use browser or curl -N
curl -N "http://127.0.0.1:18080/api/chat/stream?text=stream%20test&lang=ru"
```

### Production Testing

```powershell
# Health check (production)
curl -i https://miniapp.dmitrybond.tech/api/healthz

# Skills endpoint (production)
curl -sS "https://miniapp.dmitrybond.tech/api/skills?lang=ru" | ConvertFrom-Json | Select-Object -First 3

# Chat REST endpoint (production)
curl -i -X POST https://miniapp.dmitrybond.tech/api/chat `
  -H "Content-Type: application/json" `
  -d '{\"lang\":\"ru\",\"history\":[],\"message\":\"проверка\"}'

# Chat SSE endpoint (production)
curl -N "https://miniapp.dmitrybond.tech/api/chat/stream?text=stream%20test&lang=ru"
```

### Browser Verification

1. **Skills Page** (`/skills` or `/{lang}/skills`):
   - Open browser DevTools → Network tab
   - Navigate to `/skills` page
   - Verify request shows: `GET /api/skills?lang=ru` (or `lang=en`)
   - Response should be `200 OK` with JSON array of skill objects
   - UI should render skill cards based on the API payload

2. **Chat Endpoints**:
   - Open browser DevTools → Network tab
   - Test REST: Should see `POST /api/chat` with JSON request/response
   - Test SSE: Should see `GET /api/chat/stream?...` with `text/event-stream` content type

## Expected Responses

### `/api/healthz`
```json
{"ok": true}
```

### `/api/skills?lang=ru`
```json
[
  {
    "slug": "skill-key",
    "title": "Skill Title",
    "short": "Short description",
    "tags": ["tag1", "tag2"]
  },
  ...
]
```

### `/api/chat` (POST)
```json
{
  "reply": "Понял. Давайте начнём. проверка",
  "usage": {
    "provider": "stub",
    "tokens": 0
  }
}
```

### `/api/chat/stream` (GET)
Server-Sent Events stream:
```
event: start
data: {"ok":true}

event: token
data: {"t":"Хм… "}

event: token
data: {"t":"stream "}

event: token
data: {"t":"test "}

event: end
data: {"ok":true}
```

## Troubleshooting

### Issue: Skills page shows HTML instead of JSON
- **Cause**: Frontend is requesting `skills?lang=ru` instead of `/api/skills?lang=ru`
- **Fix**: Verify `VITE_API_BASE_URL=/api` is set in build environment
- **Check**: Browser Network tab should show request to `/api/skills`, not `/skills`

### Issue: `/api/chat` returns 404
- **Cause**: Backend router not properly registered
- **Fix**: Verify `app.include_router(api_router)` is called in `main.py`
- **Check**: Backend logs should show `/api/chat` in registered routes

### Issue: CORS errors
- **Cause**: Frontend origin not in CORS allowed origins
- **Fix**: Verify `CORS_ORIGINS` environment variable includes frontend domain
- **Check**: Backend logs for CORS middleware configuration

### Issue: Mixed content errors (HTTP/HTTPS)
- **Cause**: Frontend served over HTTPS but API over HTTP
- **Fix**: Ensure API is also served over HTTPS or use same-origin requests
- **Check**: Verify `VITE_API_BASE_URL` uses relative path `/api` for same-origin

## Notes

- Caddy does not strip `/api`, so backend must serve `/api/*` endpoints
- Frontend uses `VITE_API_BASE_URL` environment variable (defaults to `/api`)
- All API calls should go through `apiUrl()` helper from `apps/miniapp-web/src/shared/api.ts`
- Skills repository uses TTL cache (refreshed on startup and via refresh endpoint)
- Chat endpoints are currently stubs and will be replaced with LLM integration later

