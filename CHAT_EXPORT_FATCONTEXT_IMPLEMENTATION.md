# Chat Export + FatContext Grok Implementation

## Summary

This document describes the implementation of chat export and FatContext Grok functionality as specified in the PRD.

## Completed Components

### Backend (API)

1. **Chat Store Service** (`apps/miniapp-api/app/services/chat_store.py`)
   - JSONL file-based storage
   - Session management with rotation
   - Export formats: JSONL, CSV, TXT
   - Basic redaction support

2. **FatContext Service** (`apps/miniapp-api/app/services/fatcontext.py`)
   - Builds context from chat history + skills
   - Truncates by message count and byte limits
   - Selects relevant skills via fuzzy matching
   - Formats context for Grok

3. **Chat Export Router** (`apps/miniapp-api/routers/chat_export.py`)
   - `POST /api/chat/event` - Append events
   - `GET /api/chat/{session_id}` - Get messages
   - `GET /api/chat/{session_id}/export.jsonl` - Export JSONL
   - `GET /api/chat/{session_id}/export.csv` - Export CSV
   - `GET /api/chat/{session_id}/export.txt` - Export TXT
   - `POST /api/chat/ask_grok` - FatContext Grok endpoint

4. **Compose Override** (`infra/compose/miniapp.chat.override.yml`)
   - Environment variables for chat storage
   - Volume mount for `/app/data/chats`

5. **Main.py Updates**
   - Router registration for chat_export

## Remaining Tasks

### Frontend (Web Mini-App)

1. **Export Modal Component**
   - Create `apps/miniapp-web/src/components/ChatExportModal.tsx`
   - Modal with 3 format buttons (JSONL, CSV, TXT)
   - Top offset: 60px (reuse from skills modal)
   - i18n support (EN/RU)

2. **Chat Component Updates** (`apps/miniapp-web/src/components/Chat.tsx`)
   - Add "Export chat" button
   - Add FatContext toggle checkbox
   - Integrate export modal
   - Call `/api/chat/ask_grok` when FatContext enabled
   - Append events to transcript via `/api/chat/event`

3. **API Client Updates** (`apps/miniapp-web/src/api/client.ts`)
   - Add functions for chat export endpoints
   - Add function for `/api/chat/ask_grok`
   - Add function for `/api/chat/event`

### Telegram Bot

1. **Export Commands** (`apps/miniapp-bot/main.py`)
   - `/exportjsonl` - Export as JSONL
   - `/exportcsv` - Export as CSV
   - `/exporttxt` - Export as TXT
   - Inline button "Export chat" with submenu

2. **FatContext Toggle**
   - Inline toggle "Use chat history: ON/OFF"
   - Route to `/api/chat/ask_grok` when enabled
   - Append events to transcript

## Implementation Notes

### Import Structure

The services are located in `apps/miniapp-api/app/services/` but routers import from `..services`. This works because:
- The package structure resolves `apps.miniapp_api.services` through the `app/` package
- Services are accessible via relative imports from routers

If imports fail, consider:
1. Creating symlinks from `apps/miniapp-api/services/` to `apps/miniapp-api/app/services/`
2. Or moving services to top-level `services/` directory

### Session Management

- Sessions are identified by UUID
- Files are named: `session-{uuid}-{yymmdd}.jsonl`
- Rotation happens when file exceeds `FAT_ROTATE_MAX_LINES` (default 1000)

### Rate Limiting

- FatContext Grok endpoint: 5 requests per 30 seconds per session
- Enforced via `SessionRateLimiter` in `chat_export.py`

### Error Handling

- 401: Grok API key not configured
- 404: Session not found
- 429: Rate limited
- 502: Grok provider unavailable
- 503: Skills unavailable

## Testing Commands

### PowerShell

```powershell
cd infra/compose

# Bring up API with chat override
docker compose --env-file .env.miniapp `
  -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml `
  -f miniapp.csv.override.yml -f miniapp.llm.override.yml -f miniapp.chat.override.yml `
  up -d --build api

# Create session via event append
$body = '{ "role":"user","content":"Привет! Это тест чата.","lang":"ru"}'
curl -s -X POST https://miniapp.dmitrybond.tech/api/chat/event -H "Content-Type: application/json" -d $body | jq .

# Export formats
$session = "<paste-session-id>"
curl -s "https://miniapp.dmitrybond.tech/api/chat/$session?limit=3" | jq .
curl -s "https://miniapp.dmitrybond.tech/api/chat/$session/export.jsonl" | head -n 3
curl -s "https://miniapp.dmitrybond.tech/api/chat/$session/export.csv"  | head -n 3

# FatContext ask
curl -s -X POST https://miniapp.dmitrybond.tech/api/chat/ask_grok `
  -H "Content-Type: application/json" `
  -d "{`"session_id`":`"$session`",`"q`":`"Можешь ли ты предложить план ETL?`",`"lang`":`"ru`"}" | jq .
```

### Bash

```bash
cd infra/compose

docker compose --env-file .env.miniapp \
  -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml \
  -f miniapp.csv.override.yml -f miniapp.llm.override.yml -f miniapp.chat.override.yml \
  up -d --build api

curl -s -X POST https://miniapp.dmitrybond.tech/api/chat/event \
  -H "Content-Type: application/json" \
  -d '{"role":"user","content":"Hi! This is a chat test.","lang":"en"}' | jq .

SESSION="<paste-session-id>"
curl -s "https://miniapp.dmitrybond.tech/api/chat/$SESSION?limit=3" | jq .
curl -s "https://miniapp.dmitrybond.tech/api/chat/$SESSION/export.jsonl" | head -n 3
curl -s "https://miniapp.dmitrybond.tech/api/chat/$SESSION/export.csv"  | head -n 3

curl -s -X POST https://miniapp.dmitrybond.tech/api/chat/ask_grok \
  -H "Content-Type: application/json" \
  -d '{"session_id":"'"$SESSION"'","q":"Can you propose an ETL plan?","lang":"en"}' | jq .
```

## Files Created/Modified

### Created
- `apps/miniapp-api/app/services/chat_store.py`
- `apps/miniapp-api/app/services/fatcontext.py`
- `apps/miniapp-api/routers/chat_export.py`
- `infra/compose/miniapp.chat.override.yml`

### Modified
- `apps/miniapp-api/main.py` - Added chat_export router

## Next Steps

1. Complete frontend export modal and integration
2. Complete Telegram bot export commands
3. Test end-to-end flow
4. Create unified diff documentation
5. Create numbered changelog

