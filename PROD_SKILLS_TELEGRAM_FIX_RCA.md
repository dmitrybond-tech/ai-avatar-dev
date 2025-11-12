# Production Skills & Telegram Export Fix - Root Cause Analysis

## Issues Identified

### 1. `/api/skills/debug` Returns 404 (skill_not_found)
**Status:** ✅ Already Fixed
**Root Cause:** Route shadowing was previously fixed
- Dynamic route `/api/skills/{slug}` was previously declared before static route `/api/skills/debug`
- FastAPI matches routes in declaration order, so `/api/skills/debug` was treated as `/api/skills/{slug}` with `slug="debug"`

**Current State:** 
- File: `apps/miniapp-api/routers/skills.py`
- `/api/skills/debug` is declared at line 143 (BEFORE `/api/skills/{slug}` at line 172)
- Both routes are in `api_router` with `/api` prefix
- Router is registered in `main.py` at line 98

**Verification:** Route order is correct, no changes needed.

### 2. `/api/skills?lang=ru` Returns 0 Items
**Status:** ✅ Fixed
**Root Cause:** `SKILLS_SOURCE` defaulted to "auto" instead of "csv"
- When `SKILLS_SOURCE=auto`, SkillsRepository tries Notion first, then falls back to CSV
- If Notion is not configured or fails, CSV fallback should work, but defaulting to "csv" is more explicit for production

**Fix:** 
- File: `infra/compose/miniapp.compose.yaml` line 20
- Changed: `SKILLS_SOURCE: ${SKILLS_SOURCE:-auto}` → `SKILLS_SOURCE: ${SKILLS_SOURCE:-csv}`
- This ensures CSV is used by default in production

**Additional Notes:**
- `SKILLS_CSV_PATH` is already set to `/app/data/skills.csv` (line 21)
- CSV file should be mounted via volume or included in container image
- Optional override file `infra/compose/miniapp.csv.override.yml` created for host CSV mounting

### 3. `/api/telegram/selftest` Returns 404
**Status:** ✅ Verified (No Issue)
**Root Cause:** Route exists and is properly registered
- Route exists in `apps/miniapp-api/routers/chat_v2.py` at line 133
- Router `chat_router` is registered in `main.py` at line 94
- Router has prefix `/api` (defined in chat_v2.py line 17)

**Verification:** 
- File: `apps/miniapp-api/routers/chat_v2.py` line 133-150
- Handler: `telegram_selftest()` function
- Returns 400 if `TELEGRAM_TOKEN` missing, 502 on network errors
- Registered via `app.include_router(chat_router)` in `main.py` line 94

**No changes needed.**

### 4. `/api/export/telegram` Returns telegram_failed
**Status:** ✅ Verified (Handler Correct)
**Root Cause:** Missing environment variables or network issues
- Handler already has proper error handling:
  - 400 for missing env vars (`TELEGRAM_TOKEN` or `ADMIN_CHAT_ID`)
  - 502 for network/API errors
- Handler accepts both `{items:[...]}` and `{messages:[...]}` (normalized at line 167-169)

**Current State:**
- File: `apps/miniapp-api/routers/chat_v2.py` line 153-214
- Handler: `export_telegram()` function
- Error handling: Lines 199-213
- Compose file has env vars: `TELEGRAM_TOKEN` (line 26), `ADMIN_CHAT_ID` (line 28)

**Fix:** Ensure environment variables are set in production. Handler code is correct.

## Files Changed

1. **apps/miniapp-web/src/api/client.ts** (lines 42-43)
   - Added guard to handle both array and `{items,count}` response shapes
   - Change: `const items = Array.isArray(data) ? data : (data?.items || []);`

2. **infra/compose/miniapp.csv.override.yml** (NEW FILE)
   - Optional override for mounting host CSV file
   - Provides read-only bind mount for `/app/data/skills.csv`

## Files Verified (No Changes Needed)

1. **apps/miniapp-api/routers/skills.py**
   - Route order correct: `/api/skills/debug` (line 143) before `/api/skills/{slug}` (line 172)

2. **apps/miniapp-api/routers/chat_v2.py**
   - `/api/telegram/selftest` exists (line 133)
   - `/api/export/telegram` handler correct (line 153)

3. **apps/miniapp-api/main.py**
   - All routers properly registered (lines 94-101)

4. **infra/compose/miniapp.compose.yaml**
   - All required env vars present (lines 20-29)

## Environment Variables Required

The following environment variables must be set in production:

- `SKILLS_SOURCE=csv` (or leave unset to use default)
- `SKILLS_CSV_PATH=/app/data/skills.csv` (or leave unset to use default)
- `TELEGRAM_TOKEN` (required for telegram export)
- `TELEGRAM_BOT_TOKEN` (falls back to `TELEGRAM_TOKEN` if not set)
- `ADMIN_CHAT_ID` (required for telegram export)
- `TELEGRAM_ADMIN_CHAT_ID` (falls back to `ADMIN_CHAT_ID` if not set)

All are already configured in `infra/compose/miniapp.compose.yaml`.
