# Skills CSV Mode Final Fix - Changelog

## Root Cause Analysis

### Issues Identified

1. **Empty State Logic**: Frontend showed "NoSkills Published Yet" on API errors (when `skills` was set to `[]` on catch)
2. **Missing Fallback**: Backend raised 503 when CSV was missing instead of using fallback
3. **Debug Endpoint**: Didn't properly show `source: "csv"|"fallback"` and count for CSV mode

### Root Causes

- **Data Contract Mismatch**: Frontend didn't distinguish between error state (network/500) and empty success (200 + [])
- **Source Selection**: Backend checked CSV existence but didn't provide fallback when CSV failed
- **URL Builder**: Already correct (`apiUrl()` returns `/api/skills`)

## Changes Made

### Backend (`apps/miniapp-api/`)

#### New File: `app/services/skills_fallback.py`
- Created fallback provider with 2 hardcoded skills (Automation, Cloud & DevOps)
- Returns `List[SkillRecord]` matching CSV loader interface

#### Modified: `routers/skills.py`
- **Removed**: `_check_csv_source()` function that raised 503 errors
- **Added**: `_load_skills_with_fallback()` function
  - Loads CSV via `get_loader().load_skills()`
  - Falls back to `get_fallback_skills()` if CSV returns 0 skills
  - Logs warning when fallback is used
- **Updated**: `_list_skills_impl()` - uses `_load_skills_with_fallback()` for CSV mode
- **Updated**: `_get_skill_impl()` - uses `_load_skills_with_fallback()` for CSV mode
- **Updated**: `search_skills_api()` - uses loader for CSV mode, repo for Notion mode
- **Updated**: `ask_skills()` - uses fallback when skills list is empty
- **Updated**: `debug_skills()` endpoint
  - For CSV mode: shows `source: "csv"|"fallback"`, `count`, `csv_path`, `csv_exists`
  - For non-CSV mode: shows existing notion/csv info

### Frontend (`apps/miniapp-web/src/`)

#### Modified: `pages/SkillsPage.tsx`
- **Added**: `status` state: `"loading" | "success" | "error"`
- **Updated**: `useEffect` for skills loading
  - Sets `status = "success"` on successful load
  - Sets `status = "error"` on catch (doesn't set `skills = []`)
  - Added temporary `console.debug('[skills:list]', ...)` logging
- **Updated**: `listContent` useMemo
  - Shows error UI only when `status === "error"`
  - Shows loading skeleton when `status === "loading" || !skills`
  - Shows "NoSkills Published Yet" only when `status === "success" && skills.length === 0`
  - Updated dependency array to include `status`

#### Modified: `api/client.ts`
- **Updated**: `getSkills()` function
  - Added temporary `console.debug('[skills:raw]', ...)` logging
  - Added temporary `console.debug('[skills:mapped]', ...)` logging

### Styling

#### Verified: `index.css`
- Modal top offset already configured: `--modal-top-offset: calc(env(safe-area-inset-top, 0px) + 60px)`
- Modal uses `modal-offset-pt` and `modal-offset-mt` classes (no changes needed)

## API Contract

### Endpoints (Unchanged)

- `GET /api/skills?lang=ru|en` → `[{ slug, title, short, tags }]`
- `GET /api/skills/{slug}?lang=ru|en` → `{ slug, title, short, tags, bullets: [], examples: [] }`
- `GET /api/skills/debug` → `{ source: "csv"|"fallback", count: N, csv_path: "...", csv_exists: bool, sample: [...] }`

## Testing

### Backend Tests

```bash
# Test list
curl -s "https://<HOST>/api/skills?lang=en" | jq '.[0]'

# Test detail
curl -s "https://<HOST>/api/skills/automation?lang=en" | jq '{slug,title,short,tags,bullets,examples}'

# Test debug
curl -s "https://<HOST>/api/skills/debug" | jq .
```

### Frontend Tests

1. **Normal**: Navigate to `/skills` → see tiles → click tile → see modal
2. **Empty (200 + [])**: Mock API to return `[]` → see "NoSkills Published Yet"
3. **Error**: Stop API → see error message with "Try again" button (not "NoSkills")
4. **Fallback**: Remove CSV → see fallback skills (2 skills) in UI

## Files Changed

### Backend
- `apps/miniapp-api/app/services/skills_fallback.py` (NEW)
- `apps/miniapp-api/routers/skills.py` (MODIFIED)

### Frontend
- `apps/miniapp-web/src/pages/SkillsPage.tsx` (MODIFIED)
- `apps/miniapp-web/src/api/client.ts` (MODIFIED)

### Documentation
- `SKILLS_CSV_MODE_FINAL_FIX_RUNBOOK.md` (NEW)
- `SKILLS_CSV_MODE_FINAL_FIX_CHANGELOG.md` (NEW)

## Notes

- Console debug logging should be removed before production merge
- Fallback provides minimal skillset (2 skills) - expand if needed
- CSV mode (`SKILLS_SOURCE=csv`) does not touch Notion repository
- CSV header aliases already support exact headers (no changes needed)

## Acceptance Criteria

✅ CSV mode shows primary tiles (grid) and secondary sections (bullets + examples) in modal  
✅ "NoSkills Published Yet" only shows on 200 + [] (not on error)  
✅ API returns stable contract; frontend uses unified adapter  
✅ CSV fallback ensures UI never empties  
✅ `/api/skills/debug` shows correct source and count  
✅ Modal top position is 60px  
✅ Minimal diffs, no unrelated changes  

