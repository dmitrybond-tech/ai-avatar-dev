# Skills CSV Alignment Changelog

## Summary

Aligned CSV loader with provided CSV headers (Title EN, Bullets EN, etc.), verified API responses power skills buttons in web & Telegram mini-app, and confirmed Grok integration remains intact. Web mini-app skills grid uses modal with 60px top offset.

## Changes

### 1. apps/miniapp-api/app/services/skills_loader.py

**Change:** Extended CSV header alias map to accept space-separated header names matching the provided CSV format.

**Details:**
- Added "title en" alias to `title_en` field
- Added "title ru" alias to `title_ru` field
- Added "short en" alias to `short_en` field
- Added "short ru" alias to `short_ru` field
- Added "bullets en" alias to `bullets_en` field
- Added "bullets ru" alias to `bullets_ru` field
- Added "examples en" alias to `examples_en` field
- Added "examples ru" alias to `examples_ru` field

**Impact:** CSV loader now correctly parses CSV files with headers like "Title EN", "Bullets EN", etc. (normalized to lowercase "title en", "bullets en", etc. during parsing).

**No breaking changes:** Existing aliases remain, ensuring backward compatibility.

### 2. apps/miniapp-api/routers/skills.py

**Status:** Verified - no changes needed.

**Details:**
- `GET /api/skills?lang=ru|en` returns array of cards with: `slug`, `title`, `short`, `tags` ✓
- `GET /api/skills/{slug}?lang=...` includes `bullets[]` and `examples[]` in selected language ✓
- `POST /api/skills/ask` contract preserved ✓

### 3. apps/miniapp-web/src/pages/SkillsPage.tsx

**Status:** Verified - no changes needed.

**Details:**
- Skills grid renders clickable buttons/tiles with title, short, tags ✓
- Modal opens on click with 60px top offset using `modal-offset-pt` and `modal-offset-mt` classes ✓
- Fetches `/api/skills?lang=<ru|en>` for list ✓
- Fetches `/api/skills/{slug}?lang=<ru|en>` for detail ✓
- Handles 503 gracefully ✓

### 4. apps/miniapp-web/src/index.css

**Status:** Verified - no changes needed.

**Details:**
- `--modal-top-offset` already set to `calc(env(safe-area-inset-top, 0px) + 60px)` ✓
- `modal-offset-pt` and `modal-offset-mt` utility classes defined ✓

### 5. SKILLS_CSV_ALIGNMENT_RUNBOOK.md (new)

**Change:** Created comprehensive runbook with PowerShell and Bash commands.

**Details:**
- Environment variable checks (SKILLS_SOURCE, SKILLS_CSV_PATH)
- CSV file existence verification (host and container)
- curl/Invoke-WebRequest tests for all skills endpoints
- Docker Compose command examples with `miniapp.llm.override.yml`
- Troubleshooting guide
- Acceptance criteria checklist

## Testing

### Manual Testing Steps

1. **CSV Loading:**
   ```bash
   # Check CSV is loaded
   curl http://localhost:18080/api/skills?lang=en | jq '.[0]'
   ```

2. **API Endpoints:**
   - List: `GET /api/skills?lang=ru` returns cards with slug, title, short, tags
   - Detail: `GET /api/skills/automation?lang=ru` returns bullets[] and examples[]
   - Ask: `POST /api/skills/ask` works with Grok integration

3. **Web Mini-App:**
   - Skills grid renders buttons
   - Clicking opens modal with 60px top offset
   - Modal shows bullets and examples

### Automated Testing

See `SKILLS_CSV_ALIGNMENT_RUNBOOK.md` for PowerShell and Bash test scripts.

## Deployment Notes

1. **No migration required** - CSV format remains compatible
2. **No environment variable changes** - existing vars work as-is
3. **Include LLM override** - remember to add `-f miniapp.llm.override.yml` to compose commands when using Grok

## Rollback

If issues occur, revert the change to `apps/miniapp-api/app/services/skills_loader.py`:

```python
# Revert CSV_ALIASES to previous version (remove space-separated aliases)
```

## Related Files

- `apps/api/data/skills.csv` - CSV file with headers: Title EN, Bullets EN, Bullets RU, Examples EN, Examples RU, Short EN, Short RU, Slug, Tags, Title RU
- `apps/miniapp-api/app/services/skills_loader.py` - CSV loader with updated aliases
- `apps/miniapp-api/routers/skills.py` - API endpoints (verified, no changes)
- `apps/miniapp-web/src/pages/SkillsPage.tsx` - Skills grid UI (verified, no changes)
- `apps/miniapp-web/src/index.css` - Modal offset CSS (verified, no changes)

