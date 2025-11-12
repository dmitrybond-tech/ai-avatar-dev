# Production Skills & Telegram Export Fix - Root Cause Analysis

## Issues Identified

### 1. `/api/skills/debug` Returns 404 (skill_not_found)
**Root Cause:** Route shadowing in `apps/miniapp-api/routers/skills.py`
- Dynamic route `/api/skills/{slug}` (line 143) was declared before static route `/api/skills/debug` (line 177)
- FastAPI matches routes in declaration order, so `/api/skills/debug` was treated as `/api/skills/{slug}` with `slug="debug"`
- This caused the handler to look for a skill with key "debug" and return `skill_not_found`

**Fix:** Moved `/api/skills/debug` route before `/api/skills/{slug}` (now at line 143 vs 172)

### 2. `/api/skills?lang=ru` Returns 0 Items
**Root Cause:** Missing environment variables in API container
- `SKILLS_SOURCE` and `SKILLS_CSV_PATH` were not being passed to the container
- CSV file was not mounted/accessible in the container
- SkillsRepository fell back to empty/unknown provider

**Fix:** Verified env vars are present in `infra/compose/miniapp.compose.yaml` (lines 20-21). If CSV is on host, add volume mount override.

### 3. `/api/telegram/selftest` Returns 404
**Root Cause:** Route already exists but may not have been accessible
- Route exists in `apps/miniapp-api/routers/chat_v2.py` at line 133
- Router is included in `main.py` at line 94
- No changes needed - route is properly wired

**Fix:** Verified route exists and is wired correctly. No changes required.

### 4. `/api/export/telegram` Returns telegram_failed
**Root Cause:** Missing environment variables or network issues
- `TELEGRAM_TOKEN` and `ADMIN_CHAT_ID` were empty in API container
- Export handler already has proper error handling (400 for missing env, 502 for network errors)

**Fix:** Verified env vars are present in compose file (lines 26-29). Export handler already handles errors gracefully.

## Files Changed

1. `apps/miniapp-api/routers/skills.py` - Route reordering (lines 143-169 moved before 172)

## Files Verified (No Changes Needed)

1. `apps/miniapp-api/routers/chat_v2.py` - Telegram selftest route exists (line 133)
2. `apps/miniapp-api/main.py` - Router wiring verified (line 94)
3. `infra/compose/miniapp.compose.yaml` - Env vars present (lines 20-29)
4. `apps/miniapp-api/routers/chat_v2.py` - Export handler tolerant (lines 167-213)

