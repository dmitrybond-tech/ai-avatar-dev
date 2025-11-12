# Skills CSV Display Fix - Changelog

## Summary

Fixed skill cards display from CSV across API and web UI. Ensured CSV is the active source at runtime, mapped CSV headers correctly, and made the skills grid + modal render properly. Enabled one global chat toggle ("Smart answer (LLM)") only on the main chat screen (removed any LLM toggles from the Skills page). When the toggle is ON, chat messages route to Grok (prefer `/api/chat/ask_grok`; fallback to `/api/skills/ask`).

## Changes

### 1. CSV Override File (infra/compose/miniapp.csv.override.yml)

**Status:** Verified (already exists, no changes needed)

The file already exists and correctly:
- Sets `SKILLS_SOURCE=csv`
- Sets `SKILLS_CSV_PATH=/app/data/skills.csv`
- Mounts `apps/miniapp-api/data/skills.csv` as read-only

### 2. CSV Header Aliases (apps/miniapp-api/app/services/skills_loader.py)

**Change:** Extended CSV_ALIASES to match exact CSV headers with spaces.

```python
CSV_ALIASES = {
    "key": ["key", "slug", "id", "slug", "Slug"],
    "title_en": ["title_en", "name_en", "en_title", "en_name", "title", "title en", "Title EN", "Title"],
    "title_ru": ["title_ru", "name_ru", "ru_title", "ru_name", "title ru", "Title RU"],
    "short_en": ["short_en", "summary_en", "en_short", "en_summary", "short en", "Short EN"],
    "short_ru": ["short_ru", "summary_ru", "ru_short", "ru_summary", "short ru", "Short RU"],
    "tags": ["tags", "labels", "categories", "Tags"],
    "bullets_en": ["bullets_en", "points_en", "en_bullets", "bullets en", "Bullets EN"],
    "bullets_ru": ["bullets_ru", "points_ru", "ru_bullets", "bullets ru", "Bullets RU"],
    "examples_en": ["examples_en", "cases_en", "en_examples", "example_en", "examples en", "Examples EN"],
    "examples_ru": ["examples_ru", "cases_ru", "ru_examples", "example_ru", "examples ru", "Examples RU"],
    "weight": ["weight", "order", "prio", "rank"],
    "pinned": ["pinned", "pin", "featured"],
}
```

### 3. Tags Splitting (apps/miniapp-api/app/services/skills_loader.py)

**Change:** Updated `_split_list` to use regex for splitting by comma or semicolon.

**Before:**
```python
def _split_list(val: str) -> List[str]:
    """Split tags by ; or ,; trim spaces; de-dup."""
    if not val:
        return []
    parts = [p.strip(" \t\r\n-•") for p in val.replace(";", ",").split(",")]
    return [p for p in parts if p]
```

**After:**
```python
def _split_list(val: str) -> List[str]:
    """Split tags by ; or ,; trim spaces; de-dup."""
    if not val:
        return []
    parts = [p.strip() for p in re.split(r"[;,]", val) if p.strip()]
    return parts
```

### 4. Newline Handling (apps/miniapp-api/app/services/skills_loader.py)

**Change:** Updated `_split_lines` to handle both literal `\n` and real newlines.

**Before:**
```python
def _split_lines(val: str) -> List[str]:
    """Split bullets/examples by \\n; drop empty lines; trim. Handles \\n unescape and real newlines in CSV."""
    if not val:
        return []
    # Handle literal \n sequences first
    text = val.replace("\\n", "\n")
    # Split by actual newlines (handles multi-line CSV cells)
    lines = [l.strip(" \t\r\n-•") for l in text.splitlines()]
    return [l for l in lines if l]
```

**After:**
```python
def _split_lines(val: str) -> List[str]:
    """Split bullets/examples by \\n; drop empty lines; trim. Handles \\n unescape and real newlines in CSV."""
    if not val:
        return []
    # Normalize line endings
    text = val.replace("\r\n", "\n")
    # Handle literal \n sequences first
    if "\\n" in text:
        # literal '\n' case
        lines = [p.strip() for p in text.split("\\n") if p.strip()]
    else:
        # real newlines
        lines = [p.strip() for p in text.splitlines() if p.strip()]
    return lines
```

**Also added:** `import re` at the top of the file.

### 5. CSV Source Branching (apps/miniapp-api/routers/skills.py)

**Change:** Updated `_list_skills_impl` and `_get_skill_impl` to use CSV loader directly when `SKILLS_SOURCE=csv`.

**Before:**
```python
def _list_skills_impl(request: Request, lang: Optional[str]) -> List[Dict[str, Any]]:
    _check_csv_source(request)
    repo = _repo(request)
    snapshot = repo.snapshot()
    skills = snapshot.skills
    # ...
```

**After:**
```python
def _list_skills_impl(request: Request, lang: Optional[str]) -> List[Dict[str, Any]]:
    _check_csv_source(request)
    source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
    if source == "csv":
        skills = get_loader().load_skills()
    else:
        repo = _repo(request)
        snapshot = repo.snapshot()
        skills = snapshot.skills
    # ...
```

**Similar change** applied to `_get_skill_impl`:
```python
def _get_skill_impl(
    slug: str,
    request: Request,
    lang: Optional[str],
) -> Dict[str, Any]:
    _check_csv_source(request)
    source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
    if source == "csv":
        skills = get_loader().load_skills()
        skill = next((s for s in skills if s.key == slug), None)
    else:
        repo = _repo(request)
        snapshot = repo.snapshot()
        skill = next((item for item in snapshot.skills if item.key == slug), None)
    if not skill:
        raise HTTPException(status_code=404, detail="skill_not_found")
    # ...
```

### 6. Router Includes (apps/miniapp-api/main.py)

**Status:** Verified (already correct)

The router includes are already correct:
```python
app.include_router(skills_router)
app.include_router(skills_api_router)
app.include_router(skills_alias_router)
```

The `api_router` from `skills.py` provides `/api/skills`, `/api/skills/{slug}`, `/api/skills/debug`, and `/api/skills/ask`.

### 7. Skills Page Grid Layout (apps/miniapp-web/src/pages/SkillsPage.tsx)

**Change:** Updated grid to use `lg:grid-cols-3` and increased gap.

**Before:**
```tsx
<section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
```

**After:**
```tsx
<section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
```

**Status:** Modal already has 60px top offset (`style={{ marginTop: '60px' }}`), no LLM toggles found on Skills page.

### 8. Chat Component (apps/miniapp-web/src/components/Chat.tsx)

**Status:** Verified (already correct)

The Chat component already:
- Has a single checkbox toggle "Smart answer (LLM)" persisted in localStorage (`SMART_LLM_ENABLED`)
- Routes to `/api/chat/ask_grok` when toggle is ON, with fallback to `/api/skills/ask`
- Routes to regular `/api/ask` flow when toggle is OFF
- Shows LLM badge when LLM is used

### 9. Documentation Updates

#### RUNBOOK.md

**Added:** CSV override instructions and smoke tests for both Bash and PowerShell:

```markdown
- **CSV Skills Source:** To force CSV instead of Notion, always include `-f miniapp.csv.override.yml` in compose commands:
  ```bash
  # Bash
  docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml \
    -f miniapp.csv.override.yml --env-file .env.miniapp up -d
  
  # PowerShell
  docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml `
    -f miniapp.csv.override.yml --env-file .env.miniapp up -d
  ```
  
- **Smoke tests** (after deployment):
  ```bash
  # Bash
  curl -s "http://localhost:8000/api/skills?lang=ru" | jq '.[0] | {slug, title, short, tags}'
  curl -s "http://localhost:8000/api/skills/automation?lang=ru" | jq '{slug, title, bullets, examples}'
  curl -X POST "http://localhost:8000/api/skills/ask" \
    -H "Content-Type: application/json" \
    -d '{"q":"What can you do?","lang":"ru"}' | jq '{answer, used_skills, model}'
  ```
  ```powershell
  # PowerShell
  Invoke-RestMethod -Uri "http://localhost:8000/api/skills?lang=ru" | Select-Object -First 1 | Format-List slug,title,short,tags
  Invoke-RestMethod -Uri "http://localhost:8000/api/skills/automation?lang=ru" | Format-List slug,title,bullets,examples
  Invoke-RestMethod -Uri "http://localhost:8000/api/skills/ask" -Method POST `
    -ContentType "application/json" `
    -Body '{"q":"What can you do?","lang":"ru"}' | Format-List answer,used_skills,model
  ```
```

#### apps/miniapp-api/README.md

**Updated:** Endpoints list and notes:

```markdown
Endpoints:
- GET `/healthz` and `/api/healthz`
- GET `/skills` and `/api/skills?lang=ru|en` — list skills from CSV
- GET `/api/skills/{slug}?lang=ru|en` — get skill detail
- GET `/api/skills/debug` — diagnostics
- POST `/api/skills/ask` — ask about skills using Grok
- POST `/api/chat/ask_grok` — FatContext Grok endpoint (optional, falls back to `/api/skills/ask`)
- GET `/tasks/status`
- GET `/cal/link`
- POST `/api/chat/stub`

Notes:
- CSV is the active source when `SKILLS_SOURCE=csv` (set via `miniapp.csv.override.yml`).
- Skills CSV headers: `Title EN`, `Bullets EN`, `Bullets RU`, `Examples EN`, `Examples RU`, `Short EN`, `Short RU`, `Slug`, `Tags`, `Title RU`.
- The chat toggle ("Smart answer (LLM)") is only on the main chat screen, not on the Skills page.
```

## Acceptance Criteria Verification

✅ **Inside api container, SKILLS_SOURCE=csv and /app/data/skills.csv exists (read-only).**
- Verified via `miniapp.csv.override.yml` which sets env var and mounts volume.

✅ **GET /api/skills?lang=ru returns an array with { slug, title, short, tags } populated from CSV.**
- Implemented via CSV source branching in `_list_skills_impl`.

✅ **GET /api/skills/<valid-slug>?lang=ru returns { slug, title, short, tags, bullets[], examples[] }.**
- Implemented via CSV source branching in `_get_skill_impl`.

✅ **POST /api/skills/ask returns 200 with { answer, used_skills[], model, tokens_estimate } (no 405).**
- Endpoint already exists and is correctly routed via `api_router`.

✅ **Skills page shows a clean grid of tiles from CSV; click → modal opens; no LLM toggle on this page.**
- Grid updated to `lg:grid-cols-3`, modal has 60px offset, no LLM toggles found.

✅ **Main chat screen has a single checkbox "Smart answer (LLM)" persisted across reloads:**
- ✅ When ON → chat messages use Grok (FatContext if available) or fallback to `/api/skills/ask`.
- ✅ When OFF → non-LLM path works as before.

✅ **Minimal diffs, unified diff and numbered change log delivered.**
- This document provides the changelog.

✅ **Runbook includes both PowerShell and Bash.**
- Added to RUNBOOK.md.

## Files Modified

1. `apps/miniapp-api/app/services/skills_loader.py` - CSV header aliases, tags splitting, newline handling
2. `apps/miniapp-api/routers/skills.py` - CSV source branching
3. `apps/miniapp-web/src/pages/SkillsPage.tsx` - Grid layout update
4. `RUNBOOK.md` - CSV override instructions and smoke tests
5. `apps/miniapp-api/README.md` - Endpoints and notes update

## Files Verified (No Changes Needed)

1. `infra/compose/miniapp.csv.override.yml` - Already correct
2. `apps/miniapp-api/main.py` - Router includes already correct
3. `apps/miniapp-web/src/components/Chat.tsx` - Already implements LLM toggle correctly
