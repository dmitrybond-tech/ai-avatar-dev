# Grok LLM Integration Changelog

## Overview
Integrates xAI Grok as the LLM provider to answer "What Dima can do" based on skills.csv. Adds robust CSV loading, exposes POST /api/skills/ask endpoint, and adds Telegram Mini-App toggle "Smart LLM reply (ON/OFF)" that routes user questions through Grok with CSV-grounded context.

## Changes

### 1. Dependencies (API Service)
**File:** `apps/miniapp-api/requirements.txt`
- Added `xai-sdk==1.4.0` (official xAI Python SDK)
- Updated `rapidfuzz==3.9.6` (from 3.6.1)

### 2. Docker Compose Override
**File:** `infra/compose/miniapp.llm.override.yml` (new)
- Adds Grok environment variables to `api` and `bot` services:
  - `LLM_PROVIDER` (default: grok)
  - `GROK_MODEL` (default: grok-4)
  - `GROK_BASE_URL` (default: https://api.x.ai)
  - `GROK_MAX_TOKENS` (default: 512)
  - `GROK_TEMPERATURE` (default: 0.3)
  - `XAI_API_KEY` (from env)

### 3. CSV Skills Loader
**File:** `apps/miniapp-api/app/services/skills_loader.py` (new)
- Robust CSV loader with:
  - UTF-8 BOM handling (`utf-8-sig` fallback)
  - `\n` unescape for bullets/examples
  - Header inference via CSV_ALIASES
  - Thread-safe caching with mtime-based reload
  - Fuzzy search using `rapidfuzz.process.extract`
- Functions:
  - `get_skills(lang)` - Get all skills
  - `find_skill(slug)` - Find by slug
  - `search_skills(query, lang, top_k=5)` - Fuzzy search
  - `load_skills()` - Load with caching

### 4. Grok LLM Client
**File:** `apps/miniapp-api/app/services/llm_grok.py` (new)
- xAI Grok client wrapper:
  - Reads env vars: `XAI_API_KEY`, `GROK_MODEL`, `GROK_BASE_URL`, `GROK_MAX_TOKENS`, `GROK_TEMPERATURE`
  - Uses `xai_sdk.Client` with 30s timeout
  - `ask_grok(system_prompt, messages)` - Core chat completion
  - `ask_with_context(user_question, skills_context)` - Convenience wrapper
  - System prompt: "You are Dima's capability assistant. Answer strictly based on the provided skills context; if missing, say what's known and avoid hallucinations."

### 5. Skills Router Updates
**File:** `apps/miniapp-api/routers/skills.py`
- Added `_check_csv_source()` helper - Returns 503 if `SKILLS_SOURCE=csv` and file missing
- Updated existing routes (`list_skills_api`, `get_skill_api`, `search_skills_api`) to check CSV source
- Added `POST /api/skills/ask` endpoint:
  - Request: `{ "q": string, "lang": "en|ru" (optional), "selected": [slug] (optional) }`
  - Response: `{ "answer": string, "used_skills": [slug], "model": string, "tokens_estimate": int }`
  - Pipeline: Load skills → Search top-K → Build context → Call Grok → Return answer
  - Error handling: 401 if `XAI_API_KEY` missing, 502 on provider error, 503 if no skills

### 6. Telegram Bot Toggle
**File:** `apps/miniapp-bot/main.py`
- Added in-memory toggle state: `_smart_llm_toggle: dict[int, bool]` (per-user, default OFF)
- Added `get_smart_llm_enabled()` and `set_smart_llm_enabled()` helpers
- Added `build_smart_llm_toggle()` - Inline keyboard button "Smart LLM reply: ON/OFF"
- Added `/smart` command handler:
  - `/smart on` - Enable Smart LLM
  - `/smart off` - Disable Smart LLM
  - `/smart` - Show current status
- Added `on_smart_llm_toggle()` callback handler for inline button
- Added `_call_skills_ask_api()` - HTTP client to call `/api/skills/ask`
- Added `on_text_message()` handler:
  - When Smart LLM enabled and user sends text → Call API → Reply with Grok answer
  - Includes toggle button in reply
  - Handles timeouts and errors gracefully
- Added `API_BASE_URL` env var (default: `http://api:8000`)

## Environment Variables

Add to `.env.miniapp` (do not commit secrets):

```bash
# xAI / Grok
XAI_API_KEY=__SET_ME_IN_PROD__
LLM_PROVIDER=grok
GROK_MODEL=grok-4
GROK_BASE_URL=https://api.x.ai
GROK_MAX_TOKENS=512
GROK_TEMPERATURE=0.3
```

## Testing

### PowerShell Commands

```powershell
# Set env vars
$Env:XAI_API_KEY = "<paste-key>"
$Env:LLM_PROVIDER = "grok"
$Env:GROK_MODEL = "grok-4"
$Env:GROK_BASE_URL = "https://api.x.ai"
$Env:GROK_MAX_TOKENS = "512"
$Env:GROK_TEMPERATURE = "0.3"

# Sanity check
$vars = "XAI_API_KEY","LLM_PROVIDER","GROK_MODEL","GROK_BASE_URL"
$vars | ForEach-Object { if (-not $Env:$_) { throw "Env $_ is empty" } }

# Rebuild and restart
cd infra/compose
docker compose --env-file .env.miniapp `
  -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.llm.override.yml `
  build api

docker compose --env-file .env.miniapp `
  -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.llm.override.yml `
  up -d api bot

# Probes
curl -i https://miniapp.dmitrybond.tech/api/healthz
curl -s https://miniapp.dmitrybond.tech/api/skills?lang=ru | jq '.[0]'
curl -s -X POST https://miniapp.dmitrybond.tech/api/skills/ask `
  -H "Content-Type: application/json" `
  -d '{"q":"Можешь ли ты автоматизировать ETL на Python?","lang":"ru"}' | jq .
```

### Bash Commands

```bash
export XAI_API_KEY="<paste-key>"
export LLM_PROVIDER=grok
export GROK_MODEL=grok-4
export GROK_BASE_URL=https://api.x.ai
export GROK_MAX_TOKENS=512
export GROK_TEMPERATURE=0.3

cd /srv/ai-avatar/infra/compose

# Append to .env.miniapp (edit securely on prod)
printf "\nXAI_API_KEY=%s\nLLM_PROVIDER=%s\nGROK_MODEL=%s\nGROK_BASE_URL=%s\nGROK_MAX_TOKENS=%s\nGROK_TEMPERATURE=%s\n" \
  "$XAI_API_KEY" "$LLM_PROVIDER" "$GROK_MODEL" "$GROK_BASE_URL" "$GROK_MAX_TOKENS" "$GROK_TEMPERATURE" >> .env.miniapp

docker compose --env-file .env.miniapp \
  -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.llm.override.yml \
  build api

docker compose --env-file .env.miniapp \
  -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.llm.override.yml \
  up -d api bot

# Probes
curl -i https://miniapp.dmitrybond.tech/api/healthz
curl -s https://miniapp.dmitrybond.tech/api/skills?lang=en | jq '.[0]'
curl -s -X POST https://miniapp.dmitrybond.tech/api/skills/ask \
  -H "Content-Type: application/json" \
  -d '{"q":"Can you manage migrations and ETL in Python?","lang":"en"}' | jq .
```

## Acceptance Criteria

✅ `GET /api/skills?lang=en|ru` returns CSV-backed skills  
✅ `GET /api/skills/{slug}` returns skill item  
✅ `POST /api/skills/ask` returns grounded answer and `used_skills` (≥1 if relevant)  
✅ Telegram: Inline button shows "Smart LLM reply: ON/OFF" and toggles state  
✅ When ON, user's free-form question flows to Grok and replies in ≤30s  
✅ All dependencies pinned (`xai-sdk==1.4.0`, `rapidfuzz==3.9.6`)  
✅ Compose override adds env vars to `api` and `bot`  
✅ No secrets committed  

## Files Changed

1. `apps/miniapp-api/requirements.txt` - Added xai-sdk and updated rapidfuzz
2. `infra/compose/miniapp.llm.override.yml` - New compose override
3. `apps/miniapp-api/app/services/skills_loader.py` - New CSV loader module
4. `apps/miniapp-api/app/services/llm_grok.py` - New Grok client module
5. `apps/miniapp-api/routers/skills.py` - Added /api/skills/ask endpoint and CSV checks
6. `apps/miniapp-bot/main.py` - Added Smart LLM toggle and handlers

## Notes

- CSV loader uses mtime-based caching for performance
- Grok client handles both `chat.completions.create` and `chat.create` API patterns
- Bot toggle state is in-memory (process-lifetime), no DB migration needed
- Error handling: 401 (missing key), 502 (provider error), 503 (CSV missing)
- Timeouts: 30s for chat API calls
- No prompts or API keys logged

