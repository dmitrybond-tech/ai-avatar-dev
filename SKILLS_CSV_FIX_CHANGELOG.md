# Skills CSV Fix Changelog

## Summary

Fixed skills functionality to work correctly with CSV source in both web mini-app and Telegram flow. Added Smart LLM (Grok) toggle support, fixed CSV header mapping, ensured all API endpoints respond correctly, and added robust CSV fallback when Notion is unavailable.

## Changes

### 1. Compose Override: Force CSV Source

**File:** `infra/compose/miniapp.csv.override.yml`

- Added `SKILLS_SOURCE=csv` environment variable
- Added `SKILLS_CSV_PATH=/app/data/skills.csv` environment variable
- Updated volume mount path to `../../apps/miniapp-api/data/skills.csv:/app/data/skills.csv:ro`

**Impact:** When using this override, the API container will use CSV as the skills source instead of Notion.

### 2. CSV Loader Header Aliases

**Files:**
- `apps/miniapp-api/app/services/skills_loader.py`
- `apps/miniapp-api/app/services/skills.py`

- Extended `CSV_ALIASES` to support exact CSV headers:
  - `Title EN` → `title_en`
  - `Title RU` → `title_ru`
  - `Short EN` → `short_en`
  - `Short RU` → `short_ru`
  - `Bullets EN` → `bullets_en`
  - `Bullets RU` → `bullets_ru`
  - `Examples EN` → `examples_en`
  - `Examples RU` → `examples_ru`
  - `Slug` → `key`
  - `Tags` → `tags`

**Impact:** CSV files with these exact headers are now correctly parsed.

### 3. CSV Parsing Improvements

**Files:**
- `apps/miniapp-api/app/services/skills_loader.py`
- `apps/miniapp-api/app/services/skills.py`

- Updated `_split_lines()` to handle both literal `\n` sequences and real newlines in CSV cells
- Added UTF-8 BOM support in `_load_csv()` function
- Fixed nested loop bug in CSV parsing

**Impact:** Bullets and examples with multi-line content are correctly parsed.

### 4. Skills Repository Fallback Logic

**File:** `apps/miniapp-api/app/services/skills.py`

- Added CSV fallback when `SKILLS_SOURCE=notion` but Notion is unavailable
- Ensures skills are always available even if Notion fails

**Impact:** System gracefully falls back to CSV when Notion is unavailable.

### 5. API Endpoints Verification

**File:** `apps/miniapp-api/routers/skills.py`

- Verified `GET /api/skills` endpoint works correctly
- Verified `GET /api/skills/{slug}` endpoint works correctly
- Verified `POST /api/skills/ask` endpoint exists and works correctly
- Confirmed `/api/skills/debug` is declared before dynamic `/{slug}` route

**Impact:** All endpoints respond correctly with CSV data.

### 6. Web Mini-App: Smart LLM Toggle and Ask Grok Button

**Files:**
- `apps/miniapp-web/src/pages/SkillsPage.tsx`
- `apps/miniapp-web/src/api/client.ts`

- Added `smartLLM` state toggle in SkillsPage header
- Added `askSkills()` function to API client
- Added "Ask Grok about this skill" section in skill detail modal
- Added input field and button for asking questions
- Added error handling and answer display
- Set modal top offset to 60px (via inline style)

**Impact:** Users can toggle Smart LLM mode and ask Grok questions about specific skills.

### 7. Telegram Bot: Smart LLM Toggle

**File:** `apps/miniapp-bot/main.py`

- Verified Smart LLM toggle functionality exists
- Confirmed `/smart on|off` commands work
- Confirmed inline keyboard toggle button works
- Verified text messages are sent to `/api/skills/ask` when toggle is ON

**Impact:** Bot users can enable Smart LLM replies via toggle or commands.

### 8. Documentation Updates

**Files:**
- `infra/compose/docs/deploy-miniapp.md`
- `README.md`
- `RUNBOOK.md`

- Added CSV override usage instructions to all compose command examples
- Documented `-f miniapp.csv.override.yml` flag usage
- Explained `SKILLS_SOURCE=csv` environment variable

**Impact:** Developers know how to use CSV override for skills source.

## API Endpoints

### GET /api/skills?lang=ru|en
Returns array of skill cards: `[{slug, title, short, tags}]`

### GET /api/skills/{slug}?lang=ru|en
Returns full skill detail: `{slug, title, short, tags, bullets[], examples[]}`

### POST /api/skills/ask
Request: `{q: string, lang?: "ru"|"en", selected?: string[]}`
Response: `{answer: string, used_skills: string[], model: string, tokens_estimate: number}`

## CSV Format

Supported headers (case-insensitive):
- `Title EN`, `Title RU`
- `Short EN`, `Short RU`
- `Bullets EN`, `Bullets RU` (supports newlines)
- `Examples EN`, `Examples RU` (supports newlines)
- `Slug`
- `Tags` (comma or semicolon separated)

## Testing

### PowerShell Commands
```powershell
# Check CSV override
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml -f infra/compose/miniapp.csv.override.yml config | Select-String "SKILLS_SOURCE"

# Test API endpoints
curl http://localhost:8081/api/skills?lang=ru
curl http://localhost:8081/api/skills/integrations-apis?lang=ru
curl -X POST http://localhost:8081/api/skills/ask -H "Content-Type: application/json" -d '{"q":"What can you do with APIs?","lang":"en"}'
```

### Bash Commands
```bash
# Check CSV override
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml -f infra/compose/miniapp.csv.override.yml config | grep SKILLS_SOURCE

# Test API endpoints
curl http://localhost:8081/api/skills?lang=ru
curl http://localhost:8081/api/skills/integrations-apis?lang=ru
curl -X POST http://localhost:8081/api/skills/ask -H "Content-Type: application/json" -d '{"q":"What can you do with APIs?","lang":"en"}'
```

## Acceptance Criteria Met

✅ Inside api container: `SKILLS_SOURCE=csv` and `/app/data/skills.csv` exists (ro)  
✅ `GET /api/skills?lang=ru` → array of cards with data from CSV  
✅ `GET /api/skills/integrations-apis?lang=ru` → full card from CSV (not skill_not_found)  
✅ `POST /api/skills/ask` → 200 and meaningful response from Grok  
✅ Web mini-app: skill buttons clickable, modal with 60px offset, Smart LLM toggle works  
✅ Bot: inline toggle ON/OFF clickable and changes behavior  

## Files Changed

1. `infra/compose/miniapp.csv.override.yml` - Added CSV source env vars and volume mount
2. `apps/miniapp-api/app/services/skills_loader.py` - Updated header aliases and parsing
3. `apps/miniapp-api/app/services/skills.py` - Updated header aliases, parsing, and fallback logic
4. `apps/miniapp-api/routers/skills.py` - Verified endpoints (no changes needed)
5. `apps/miniapp-web/src/pages/SkillsPage.tsx` - Added Smart LLM toggle and Ask Grok UI
6. `apps/miniapp-web/src/api/client.ts` - Added `askSkills()` function
7. `apps/miniapp-bot/main.py` - Verified Smart LLM toggle (no changes needed)
8. `infra/compose/docs/deploy-miniapp.md` - Added CSV override documentation
9. `README.md` - Added CSV override documentation
10. `RUNBOOK.md` - Added CSV override documentation

## Notes

- All changes are minimal and focused
- No secrets committed
- No heavy dependencies added
- Backward compatible (CSV fallback when Notion unavailable)
- Deterministic (pinned dependencies unchanged)

