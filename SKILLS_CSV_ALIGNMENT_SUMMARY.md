# Skills CSV Alignment - Implementation Summary

## Objective

Align CSV loader with provided CSV headers, ensure API responses power skills buttons (web & Telegram mini-app), and keep Grok integration intact. Render skills grid in web mini-app with 60px top offset modal.

## Changes Made

### 1. CSV Loader Updates
**File:** `apps/miniapp-api/app/services/skills_loader.py`

Extended `CSV_ALIASES` to accept space-separated header names:
- Added "title en" → `title_en`
- Added "title ru" → `title_ru`
- Added "short en" → `short_en`
- Added "short ru" → `short_ru`
- Added "bullets en" → `bullets_en`
- Added "bullets ru" → `bullets_ru`
- Added "examples en" → `examples_en`
- Added "examples ru" → `examples_ru`

**Impact:** CSV loader now correctly parses CSV files with headers like "Title EN", "Bullets EN", etc.

### 2. API Endpoints (Verified - No Changes)
**File:** `apps/miniapp-api/routers/skills.py`

- ✅ `GET /api/skills?lang=ru|en` returns cards with `slug`, `title`, `short`, `tags`
- ✅ `GET /api/skills/{slug}?lang=...` includes `bullets[]` and `examples[]`
- ✅ `POST /api/skills/ask` contract preserved

### 3. Web Mini-App (Verified - No Changes)
**Files:** 
- `apps/miniapp-web/src/pages/SkillsPage.tsx`
- `apps/miniapp-web/src/index.css`

- ✅ Skills grid renders clickable buttons
- ✅ Modal opens with 60px top offset (`modal-offset-pt` and `modal-offset-mt` classes)
- ✅ Handles 503 gracefully

## Deliverables

1. ✅ **Unified Diff** - `SKILLS_CSV_ALIGNMENT_UNIFIED_DIFF.md`
2. ✅ **Changelog** - `SKILLS_CSV_ALIGNMENT_CHANGELOG.md`
3. ✅ **Runbook** - `SKILLS_CSV_ALIGNMENT_RUNBOOK.md` (PowerShell & Bash commands)

## Testing

See `SKILLS_CSV_ALIGNMENT_RUNBOOK.md` for comprehensive test commands.

Quick test:
```bash
# List skills
curl http://localhost:18080/api/skills?lang=en | jq '.[0]'

# Get skill detail
curl http://localhost:18080/api/skills/automation?lang=en | jq '.bullets'
```

## Deployment

1. No migration required
2. No environment variable changes
3. Include `-f miniapp.llm.override.yml` in compose commands when using Grok

## Acceptance Criteria

- ✅ GET /api/skills?lang=ru shows CSV rows mapped correctly (cards with slug/title/short/tags)
- ✅ GET /api/skills/{slug}?lang=ru returns bullets[] and examples[]
- ✅ Web mini-app renders skills grid with clickable buttons; modal opens with 60px top offset
- ✅ POST /api/skills/ask remains working; Grok answers reference used_skills from CSV
- ✅ No secrets, minimal diffs, all tests/runs scripted

## Files Changed

- **Modified:** 1 file (`apps/miniapp-api/app/services/skills_loader.py`)
- **Verified:** 4 files (no changes needed)
- **Created:** 3 documentation files

**Total:** 8 lines changed (added space-separated header aliases)

