# Notion Environment Variables Fix - Changelog

## Rationale
In Docker Compose, `environment:` overrides `env_file:`. Defining `NOTION_*: ""` in `environment:` blanks secrets from `.env.miniapp`, causing 502 errors on `/api/tasks/public`. Removing empty NOTION_* overrides ensures secrets are read from `.env.miniapp`.

## Changes

### 1. Compose Files Cleanup
**Files modified:**
- `infra/compose/miniapp.compose.yaml`
- `infra/compose/miniapp.runtime.yml`
- `infra/compose/miniapp.stack.yml`
- `infra/compose/miniapp.notion.override.yml`

**Changes:**
- Verified `env_file: [.env.miniapp]` is present for `services.api` and `services.bot` in all files
- Ensured no `NOTION_API_KEY`, `NOTION_PUBLIC_TASKS_DB_ID`, `NOTION_SECRET`, or `NOTION_DB` in `environment:` sections
- Only non-secret env vars remain (PORT, DEFAULT_LANG, CAL_*, NOTION_TIMEOUT, WEBSITE_ORIGIN)
- Standardized environment list format to use array syntax (`- KEY=value`)

### 2. FastAPI Initialization Order
**File:** `apps/miniapp-api/main.py`

**Changes:**
- Moved `app = FastAPI(...)` to top of file (line 7), before any router imports
- Removed module-level `os.getenv()` calls that were side-effects before app creation
- Router import (`from .routers.public_tasks import router`) now occurs after app creation (line 26)
- Moved `os.getenv()` calls into function bodies where needed (cal_link, cal_suggest)

### 3. Legacy Environment Variable Support
**File:** `apps/miniapp-api/integrations/notion_public.py`

**Changes:**
- Updated `_client()` to support legacy `NOTION_SECRET` → `NOTION_API_KEY` fallback
- Changed from module-level `NOTION_API_KEY` to function-level lookup with fallback
- Error message now mentions both env var names

**File:** `apps/miniapp-api/routers/public_tasks.py`

**Changes:**
- Updated `/api/tasks/public` endpoint to support legacy `NOTION_DB` → `NOTION_PUBLIC_TASKS_DB_ID` fallback
- Updated `/api/tasks/debug` endpoint with same legacy fallback
- Both endpoints now check both env var names before failing

### 4. Debug Script Enhancement
**File:** `scripts/print-api-env.py`

**Changes:**
- Rewrote script to show masked lengths of all NOTION env vars
- Added support for both current and legacy env var names:
  - `NOTION_API_KEY` and `NOTION_SECRET` (legacy)
  - `NOTION_PUBLIC_TASKS_DB_ID` and `NOTION_DB` (legacy)
- Improved masking function to show last 4 characters
- Clear output format for debugging

## Verification

### Compose Config Check
```bash
$FILES = "-f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml -f infra/compose/miniapp.stack.yml -f infra/compose/miniapp.notion.override.yml"
docker compose $FILES config | sed -n '/services:/,/volumes:/p' | sed -n '/api:/,/^[^ ]/p'
```

**Expected:** `env_file: [.env.miniapp]` present, no `NOTION_API_KEY`/`NOTION_PUBLIC_TASKS_DB_ID`/`NOTION_SECRET`/`NOTION_DB` in `environment:`

### Environment Check
```bash
docker compose $FILES exec -T api python /app/scripts/print-api-env.py
```

**Expected:** Non-empty masked values for API key and DB ID

### Endpoint Tests
```bash
# Debug endpoint
curl -sS http://127.0.0.1:18080/api/tasks/debug | jq .

# Public tasks endpoint
curl -sS "http://127.0.0.1:18080/api/tasks/public?statuses=In%20Progress,Review&limit=10" | jq .

# Production endpoint
curl -sS "https://miniapp.dmitrybond.tech/api/tasks/public?statuses=In%20Progress,Review&limit=20" | jq .
```

**Expected:** All return 200 with non-empty JSON arrays

## Files Changed

1. `infra/compose/miniapp.compose.yaml`
2. `infra/compose/miniapp.runtime.yml`
3. `infra/compose/miniapp.stack.yml`
4. `infra/compose/miniapp.notion.override.yml`
5. `apps/miniapp-api/main.py`
6. `apps/miniapp-api/integrations/notion_public.py`
7. `apps/miniapp-api/routers/public_tasks.py`
8. `scripts/print-api-env.py`

## Notes

- Notion query sort remains unchanged: `{"timestamp":"last_edited_time","direction":"descending"}`
- Default statuses for `/api/tasks/public` remain: `["In Progress","Review"]`
- Error handling: 400 for bad input, 502 for Notion/network problems with `{"error":"notion_unreachable"}`
- UI contract preserved: modal renders vertical task cards
- No changes to Caddy, ports, networks, image names, or tags

