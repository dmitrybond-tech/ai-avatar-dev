# Skills Primary/Secondary + Chat Toggle Wiring - Changelog

**Date:** 2025-01-XX  
**Version:** v0.3.0  
**Scope:** Skills page grid + modal, chat LLM toggle wiring, CSV adapter normalization

---

## Summary

Implemented Skills page with primary tiles grid and secondary modal (bullets + examples), added data adapter for API normalization, wired chat LLM toggle to message submit flow, and ensured backend CSV loading works correctly with proper router includes.

---

## Changes

### 1. Web Data Adapter (`apps/miniapp-web/src/shared/skillsAdapter.ts`)

**New File:** Created adapter to normalize API responses to UI model.

#### Functions
- `mapList(api: any[]): SkillListItem[]` - Normalizes list API responses, tolerant to legacy fields (key/name/summary)
- `mapDetail(x: any): SkillDetail` - Normalizes detail API responses with bullets and examples

#### Types
- `SkillListItem` - { slug, title, short, tags }
- `SkillDetail` - SkillListItem + { bullets, examples }

**Purpose:** Single source of truth for API → UI data transformation, handles both new and legacy field names.

---

### 2. API Client Updates (`apps/miniapp-web/src/api/client.ts`)

#### Updated Functions
- `getSkills()` - Now uses `/api/skills` endpoint (was `/skills`) and `mapList()` adapter
- `getSkillDetail()` - Now uses `/api/skills/{slug}` endpoint (was `/skills/{slug}`) and `mapDetail()` adapter

**Impact:** Ensures consistent API paths and normalized data format.

---

### 3. Skills Page UI (`apps/miniapp-web/src/pages/SkillsPage.tsx`)

#### Modal Top Offset
- Changed from inline `style={{ marginTop: '60px' }}` to CSS class `modal-offset-mt`
- Uses CSS variable `--modal-top-offset: calc(env(safe-area-inset-top, 0px) + 60px)` from `index.css`

**Impact:** Consistent 60px top offset across all modals, respects safe area insets.

---

### 4. Skill Detail View (`apps/miniapp-web/src/components/SkillDetail.tsx`)

#### Bullets Section
- Changed from `list-disc` bullets to checklist-style with checkmark (✓)
- Section label: "Что делаю" (ru) / "What I do" (en)
- Each bullet rendered as flex row with checkmark icon

#### Examples Section
- Section label: "Примеры" (ru) / "Examples" (en)
- Examples rendered as cards with border and background (`rounded-md border border-gray-200 bg-gray-50 px-3 py-2`)

**Impact:** Better visual hierarchy, bullets appear as actionable checklist items.

---

### 5. Chat Toggle Wiring (`apps/miniapp-web/src/components/Chat.tsx`)

**Status:** ✅ Already correctly implemented

#### Current Implementation
- Toggle uses `useSmartLLM()` hook (localStorage-backed)
- Only rendered on main chat screen (not Skills page)
- Message submit flow:
  - `smartLLM && config.llmAvailable` → tries `/api/chat/ask_grok`, falls back to `/api/skills/ask`
  - `!smartLLM` → uses `/api/ask` (local flow)
- Checkbox disabled when `!config.llmAvailable`
- i18n labels: "Умный ответ (LLM)" (ru) / "Smart answer (LLM)" (en)

**No changes needed.**

---

### 6. Backend Router Includes (`apps/miniapp-api/main.py`)

**Status:** ✅ Already correctly configured

#### Current Router Registration (lines 99-101)
```python
app.include_router(skills_router)        # /skills
app.include_router(skills_api_router)   # /api/skills, /api/skills/ask, /api/skills/debug
app.include_router(skills_alias_router) # /rules (legacy alias)
```

#### Skills Router Endpoints (`apps/miniapp-api/routers/skills.py`)
- `GET /api/skills?lang=ru|en` → list skills
- `GET /api/skills/{slug}?lang=ru|en` → skill detail
- `GET /api/skills/debug` → diagnostics (declared BEFORE `/{slug}` to avoid shadowing)
- `POST /api/skills/ask` → LLM ask endpoint

**No changes needed.**

---

### 7. CSV Loading (`apps/miniapp-api/app/services/skills_loader.py`)

**Status:** ✅ Already correctly implemented

#### CSV Header Aliases
- Supports exact headers: `Title EN`, `Bullets EN`, `Bullets RU`, `Examples EN`, `Examples RU`, `Short EN`, `Short RU`, `Slug`, `Tags`, `Title RU`
- Tolerant to legacy field names via `CSV_ALIASES` mapping
- Handles comma/semicolon splitting for tags
- Handles literal `\n` and real newlines for bullets/examples

#### Skills Router CSV Integration
- `_check_csv_source()` validates CSV file exists when `SKILLS_SOURCE=csv`
- `_list_skills_impl()` and `_get_skill_impl()` use `get_loader().load_skills()` when CSV mode
- `POST /api/skills/ask` uses CSV loader for skills context

**No changes needed.**

---

## API Contract

### GET `/api/skills?lang=ru|en`
**Response:** `[{ slug, title, short, tags }]`

### GET `/api/skills/{slug}?lang=ru|en`
**Response:** `{ slug, title, short, tags, bullets: [], examples: [] }`

### POST `/api/skills/ask`
**Request:** `{ q: string, lang?: "ru"|"en", selected?: string[] }`  
**Response:** `{ answer: string, used_skills: string[], model: string, tokens_estimate: number }`

---

## Testing Checklist

- [x] Skills page renders grid of primary tiles
- [x] Clicking tile opens modal with 60px top offset
- [x] Modal shows bullets as checklist (✓)
- [x] Modal shows examples as cards
- [x] Chat toggle only on main chat screen (not Skills page)
- [x] Chat toggle ON → calls LLM endpoint (`/api/chat/ask_grok` or `/api/skills/ask`)
- [x] Chat toggle OFF → calls local flow (`/api/ask`)
- [x] No 404/405 errors on `/api/skills/*` endpoints
- [x] CSV loading works at runtime
- [x] i18n respected (ru/en)

---

## Files Changed

1. `apps/miniapp-web/src/shared/skillsAdapter.ts` (new)
2. `apps/miniapp-web/src/api/client.ts` (updated)
3. `apps/miniapp-web/src/pages/SkillsPage.tsx` (updated)
4. `apps/miniapp-web/src/components/SkillDetail.tsx` (updated)

---

## Notes

- Backend routers were already correctly configured, no changes needed
- CSV loader was already robust, no changes needed
- Chat toggle wiring was already correct, no changes needed
- Modal CSS classes (`modal-offset-mt`) already existed in `index.css`
- Minimal diff approach: only added adapter and updated UI components

