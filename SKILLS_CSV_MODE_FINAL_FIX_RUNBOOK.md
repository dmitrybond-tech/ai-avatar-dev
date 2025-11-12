# Skills CSV Mode Final Fix - Runbook

## Overview

This runbook documents the final fix for Skills CSV mode, ensuring stable API contracts, proper fallback handling, and correct UI empty states.

## Changes Summary

### Backend (FastAPI)

1. **Fallback Provider** (`apps/miniapp-api/app/services/skills_fallback.py`)
   - Created hardcoded fallback with 2-3 skills
   - Used when CSV file is missing or parsing fails

2. **Router Updates** (`apps/miniapp-api/routers/skills.py`)
   - Added `_load_skills_with_fallback()` function
   - Removed `_check_csv_source()` that raised 503 errors
   - Updated all endpoints to use fallback when CSV fails
   - Updated `/api/skills/debug` to show `source: "csv"|"fallback"` and `count`

3. **CSV Loader** (`apps/miniapp-api/app/services/skills_loader.py`)
   - CSV header aliases already support exact headers: `Title EN`, `Bullets EN`, `Bullets RU`, `Examples EN`, `Examples RU`, `Short EN`, `Short RU`, `Slug`, `Tags`, `Title RU`
   - Proper splitting of bullets/examples (handles `\n` literals and real newlines)
   - Proper tag splitting (handles `;` and `,` separators)

### Frontend (React/TypeScript)

1. **Empty State Logic** (`apps/miniapp-web/src/pages/SkillsPage.tsx`)
   - Added `status` state: `"loading" | "success" | "error"`
   - "NoSkills Published Yet" only shows when `status === "success" && skills.length === 0`
   - Error state shows error message with Retry button (not "NoSkills")
   - Added temporary console debug logging

2. **Modal Position** (`apps/miniapp-web/src/index.css`)
   - Already configured: `--modal-top-offset: calc(env(safe-area-inset-top, 0px) + 60px)`
   - Modal uses `modal-offset-pt` and `modal-offset-mt` classes

3. **Adapter** (`apps/miniapp-web/src/shared/skillsAdapter.ts`)
   - Already provides strict mapping: `mapList()` and `mapDetail()`
   - Tolerant to legacy fields but outputs unified format

## API Contract

### Endpoints

#### `GET /api/skills?lang=ru|en`
Returns: `[{ slug, title, short, tags }]`

#### `GET /api/skills/{slug}?lang=ru|en`
Returns: `{ slug, title, short, tags, bullets: [], examples: [] }`

#### `GET /api/skills/debug`
Returns:
```json
{
  "source": "csv" | "fallback",
  "count": 7,
  "csv_path": "/app/data/skills.csv",
  "csv_exists": true,
  "sample": [{ "slug": "automation", "title": "Automation" }]
}
```

## Testing

### Phase 0 - Diagnostics

1. **Check frontend URL**:
   - Open browser DevTools → Network tab
   - Navigate to `/skills` page
   - Verify request goes to `/api/skills?lang=ru` (or `?lang=en`)

2. **Test backend directly**:
   ```bash
   # Replace <HOST> with your actual host
   curl -s "https://<HOST>/api/skills?lang=ru" | jq '.[0]'
   curl -s "https://<HOST>/api/skills/automation?lang=ru" | jq '{slug,title,short,tags,bullets,examples}'
   curl -s "https://<HOST>/api/skills/debug" | jq .
   ```

3. **Check CSV in container**:
   ```bash
   # In API container
   echo $SKILLS_SOURCE
   echo $SKILLS_CSV_PATH
   ls -l $SKILLS_CSV_PATH | head -n1
   ```

### Phase 1 - Backend Tests

```bash
# Test list endpoint
curl -s "https://<HOST>/api/skills?lang=en" | jq '.[0]'
# Expected: { "slug": "automation", "title": "Automation", "short": "...", "tags": [...] }

# Test detail endpoint
curl -s "https://<HOST>/api/skills/automation?lang=en" | jq '{slug,title,short,tags,bullets,examples}'
# Expected: Full skill detail with bullets and examples arrays

# Test debug endpoint
curl -s "https://<HOST>/api/skills/debug" | jq .
# Expected: { "source": "csv" | "fallback", "count": N, ... }

# Test fallback (remove CSV file temporarily)
# In container: mv /app/data/skills.csv /app/data/skills.csv.bak
curl -s "https://<HOST>/api/skills/debug" | jq '.source'
# Expected: "fallback"
curl -s "https://<HOST>/api/skills?lang=en" | jq 'length'
# Expected: 2 (fallback has 2 skills)
# Restore: mv /app/data/skills.csv.bak /app/data/skills.csv
```

### Phase 2 - Frontend Tests

1. **Normal operation**:
   - Navigate to `/skills` page
   - Should see grid of skill tiles
   - Click a tile → modal opens with detail
   - Check browser console for debug logs: `[skills:raw]` and `[skills:mapped]`

2. **Empty state (200 + [])**:
   - Temporarily empty CSV or mock API to return `[]`
   - Should show "No skills are published yet." (not error)

3. **Error state**:
   - Stop API server or block `/api/skills` endpoint
   - Should show error message with "Try again" button (not "NoSkills")

4. **Modal position**:
   - Open skill detail modal
   - Verify modal top is at 60px from viewport top

## Environment Variables

Required for CSV mode:
- `SKILLS_SOURCE=csv` (or leave unset, defaults to "auto")
- `SKILLS_CSV_PATH=/app/data/skills.csv` (or leave unset, uses default)

## CSV Format

Expected headers (exact match):
```
Title EN,Bullets EN,Bullets RU,Examples EN,Examples RU,Short EN,Short RU,Slug,Tags,Title RU
```

Example row:
```
Automation,"Build ETL/ELT pipelines
Write migration scripts","Проектирование ETL/ELT-пайплайнов
Скрипты миграций","Clean CSV → PostgreSQL","Ночной импорт CSV → PostgreSQL","Python ETL/ELT, migrations","Python ETL/ELT, миграции",automation,"python, etl, migrations",Автоматизация
```

## Acceptance Criteria

✅ In CSV mode, list and detail endpoints return correct data  
✅ UI renders tiles and modal correctly  
✅ "NoSkills Published Yet" only shows on 200 + empty array  
✅ Error state shows error message (not "NoSkills")  
✅ When CSV is missing/corrupted, fallback is used (UI never empty)  
✅ `/api/skills/debug` shows correct `source` and `count`  
✅ Modal top position is 60px  
✅ Minimal diffs, no unrelated changes  

## Rollback

If issues occur:

1. **Backend**: Revert changes to `apps/miniapp-api/routers/skills.py` and remove `apps/miniapp-api/app/services/skills_fallback.py`
2. **Frontend**: Revert changes to `apps/miniapp-web/src/pages/SkillsPage.tsx`

## Notes

- Console debug logging (`console.debug`) should be removed before merge to production
- Fallback skills are minimal (2 skills) - expand if needed
- CSV mode does not touch Notion repository when `SKILLS_SOURCE=csv`

