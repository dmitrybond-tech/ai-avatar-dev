# Brief Upload 404 Fix - Changelog

## Summary
Fixed 404 errors on `/briefs/upload` and `/api/briefs/upload` endpoints by ensuring proper nginx proxy configuration and completing the production-safe upload flow with idempotency, Telegram notifications, and Notion integration.

## Changes

### 1. Nginx Configuration (`apps/miniapp-web/nginx/default.conf`)
- Added `proxy_request_buffering off;` to `/briefs/` and `/api/briefs/` locations to enable streaming uploads
- Added `proxy_read_timeout 300s` and `proxy_connect_timeout 60s` for large file uploads
- `client_max_body_size 64m` already configured

### 2. API Startup Logs (`apps/api/src/app/main.py`)
- Added Telegram env var checks (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`) to startup logs alongside existing Notion checks
- Logs presence (boolean) without exposing secrets

### 3. Idempotency Fix (`apps/api/src/app/utils/idempotency.py`)
- Fixed Redis operations to run in thread pool using `asyncio.to_thread()` to avoid blocking the event loop
- Maintains existing Redis/FS fallback behavior

### 4. Existing Implementation Verified
The following components were already correctly implemented and require no changes:
- `apps/api/src/app/adapters/web/briefs.py`: Router with `/briefs/upload` and alias `/api/briefs/upload`
- `apps/api/src/app/services/telegram.py`: Telegram document sending with HTML caption
- `apps/api/src/app/services/notion.py`: Notion page creation in Backlog database
- `apps/api/src/app/utils/idempotency.py`: SHA256 fingerprinting with Redis/FS fallback
- `apps/miniapp-web/src/pages/BriefFormPage.tsx`: Frontend with request_id display, Copy button, resubmit blocking, and iframe resize support
- `apps/api/requirements.txt`: Already includes `redis>=5`, `notion-client>=2`, `ulid-py>=1.1.0`

## Endpoints

### POST `/briefs/upload`
- Main endpoint for brief file uploads
- Accepts multipart/form-data with: `file`, `name`, `company`, `phone`, `email`, `locale`, `message` (optional)
- Returns: `{ ok: true, request_id: "BRF-YYYYMMDD-...", notion_page_id: "...", dedup: false }`

### POST `/api/briefs/upload`
- Alias endpoint that proxies to the same handler
- Same request/response format as `/briefs/upload`

## Idempotency

- Fingerprint: `sha256(email|name|company|phone|file_hash)`
- TTL: 900 seconds (15 minutes) via `BRIEF_IDEMPOTENCY_TTL` env var
- Storage: Redis (if `REDIS_URL` set) with filesystem fallback to `/data/brief-ids/`
- Duplicate detection: Returns same `request_id` with `dedup: true` without re-processing

## Environment Variables

Required:
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_ADMIN_CHAT_ID`: Admin chat ID for notifications
- `NOTION_API_KEY`: Notion API key
- `NOTION_PUBLIC_TASKS_DB_ID`: Notion database ID for Backlog

Optional:
- `REDIS_URL`: Redis connection URL (defaults to FS fallback)
- `MAX_UPLOAD_MB`: Max upload size in MB (default: 64)
- `BRIEF_IDEMPOTENCY_TTL`: Idempotency TTL in seconds (default: 900)
- `DATA_DIR`: Data directory path (default: `/data`)

## Testing

### Test Commands (PowerShell)
```powershell
# Main path
curl.exe -sS -F "name=D" -F "company=TN" -F "phone=+31648982742" `
  -F "email=dmevbondarenko@gmail.com" -F "message=hello" -F "locale=ru" `
  -F "file=@C:\Windows\System32\drivers\etc\hosts" https://miniapp.dmitrybond.tech/briefs/upload | jq .

# Alias path
curl.exe -sS -F "name=D" -F "company=TN" -F "phone=+31648982742" `
  -F "email=dmevbondarenko@gmail.com" -F "message=hello" -F "locale=ru" `
  -F "file=@C:\Windows\System32\drivers\etc\hosts" https://miniapp.dmitrybond.tech/api/briefs/upload | jq .
```

### Expected Response
```json
{
  "ok": true,
  "request_id": "BRF-20241201-01ARZ3NDEKTSV4YZHHQ",
  "notion_page_id": "abc123...",
  "dedup": false
}
```

### Duplicate Response
```json
{
  "ok": true,
  "request_id": "BRF-20241201-01ARZ3NDEKTSV4YZHHQ",
  "notion_page_id": null,
  "dedup": true
}
```

## Acceptance Criteria

✅ Both endpoints return 200 OK with proper JSON response  
✅ Idempotency works: identical requests return same `request_id` with `dedup: true`  
✅ Telegram admin receives document with HTML caption including request_id  
✅ Notion page created in Backlog with all properties populated  
✅ Frontend shows request_id, Copy button, blocks resubmits  
✅ Iframe resize works in Telegram mini-app modal  
✅ Nginx proxies correctly with no request buffering for uploads  
✅ Startup logs show presence of Telegram and Notion env vars  

## Files Modified

1. `apps/miniapp-web/nginx/default.conf` - Added proxy_request_buffering off and timeouts
2. `apps/api/src/app/main.py` - Added Telegram env var checks to startup logs
3. `apps/api/src/app/utils/idempotency.py` - Fixed Redis operations to use thread pool

## Files Already Correct (No Changes)

1. `apps/api/src/app/adapters/web/briefs.py` - Router and alias already implemented
2. `apps/api/src/app/services/telegram.py` - Telegram service already implemented
3. `apps/api/src/app/services/notion.py` - Notion service already implemented
4. `apps/miniapp-web/src/pages/BriefFormPage.tsx` - Frontend already has all required features
5. `apps/api/requirements.txt` - Dependencies already present

