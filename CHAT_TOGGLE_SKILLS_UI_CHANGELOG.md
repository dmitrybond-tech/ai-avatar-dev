# Changelog: Chat Toggle & Skills UI Fix

## Overview
Moved "Smart answer (LLM)" checkbox to main chat form, removed LLM toggle from Skills page, completed Skills page UI, implemented LLM routing with fallback.

## Changes

### 1. Global Smart LLM State Hook
**File**: `apps/miniapp-web/src/hooks/useSmartLLM.ts` (NEW)
- Created `useSmartLLM` hook with localStorage persistence
- Storage key: `SMART_LLM_ENABLED`
- Default: `false`
- Persists state across page reloads

### 2. Chat Component Updates
**File**: `apps/miniapp-web/src/components/Chat.tsx`
- **Added imports**: `useSmartLLM`, `useI18n`, `askGrok`, `askSkills`
- **Replaced local state**: `smartEnabled` → global `smartLLM` from `useSmartLLM()`
- **Updated checkbox UI**: 
  - Uses i18n strings (`chat.smartLLM`, `chat.smartLLMOn`, `chat.smartLLMOff`, `chat.smartLLMUnavailable`)
  - Added `aria-label` for accessibility
- **Implemented LLM routing logic**:
  - When `smartLLM === true` and `config.llmAvailable === true`:
    1. Try `/api/chat/ask_grok` first (FatContext)
    2. Fallback to `/api/skills/ask` if ask_grok fails (401, 404, 502, 503)
  - When `smartLLM === false`: Use regular `/api/ask` flow (non-LLM)
- **Enhanced error handling**:
  - User-friendly messages for 401, 404, 502, 503
  - Localized error messages (EN/RU)
- **Updated mode labels**: Uses i18n (`chat.modeLLM`, `chat.modeSkills`)

### 3. Skills Page Cleanup
**File**: `apps/miniapp-web/src/pages/SkillsPage.tsx`
- **Removed**: LLM toggle checkbox from header
- **Removed**: `smartLLM` state and related handlers
- **Removed**: `askQuery`, `askLoading`, `askError`, `askAnswer` states
- **Removed**: `handleAskGrok` callback
- **Removed**: "Ask Grok about this skill" UI section from modal
- **Removed**: `askSkills` import (no longer needed)
- **Result**: Clean Skills page with grid tiles and modal only

### 4. API Client Updates
**File**: `apps/miniapp-web/src/api/client.ts`
- **Added types**: `AskGrokRequest`, `AskGrokResponse`
- **Added function**: `askGrok()` for `/api/chat/ask_grok` endpoint
- Handles errors and returns typed response

### 5. i18n Updates
**Files**: `apps/miniapp-web/src/i18n/en.json`, `apps/miniapp-web/src/i18n/ru.json`
- **Added `chat` section**:
  - `smartLLM`: "Smart answer (LLM)" / "Умный ответ (LLM)"
  - `smartLLMOn`: "On" / "Вкл"
  - `smartLLMOff`: "Off" / "Выкл"
  - `smartLLMUnavailable`: "Unavailable" / "Недоступно"
  - `modeLLM`: "Mode: LLM" / "Режим: LLM"
  - `modeSkills`: "Mode: Skills" / "Режим: Навыки"

## API Behavior

### LLM Routing Flow
1. **Smart LLM Enabled** (`smartLLM === true`):
   - Primary: `POST /api/chat/ask_grok` with `{ session_id, q, lang }`
   - Fallback: `POST /api/skills/ask` with `{ q, lang }` (if ask_grok fails)
   - Response marked as `usedLLM: true`

2. **Smart LLM Disabled** (`smartLLM === false`):
   - Uses: `POST /api/ask` with `{ messages, lang, top_k, use_llm: false }`
   - Standard non-LLM flow

### Error Handling
- **401**: "LLM service is not configured" / "Сервис LLM не настроен"
- **404**: "Session not found" / "Сессия не найдена"
- **502/503**: "LLM service temporarily unavailable" / "Сервис LLM временно недоступен"
- Fallback to `/api/skills/ask` for recoverable errors

## Testing Checklist
- [ ] Checkbox appears on main chat form
- [ ] Checkbox state persists across page reloads
- [ ] LLM routing works when checkbox enabled
- [ ] Fallback to `/api/skills/ask` works when `/api/chat/ask_grok` fails
- [ ] Non-LLM flow works when checkbox disabled
- [ ] Skills page has no LLM toggle
- [ ] Skills page grid and modal work correctly
- [ ] i18n strings display correctly (EN/RU)
- [ ] Error messages are user-friendly and localized

## Breaking Changes
None - backward compatible.

## Migration Notes
- User's localStorage preference (`SMART_LLM_ENABLED`) is preserved
- Existing chat sessions continue to work
- Skills page UI unchanged except removal of LLM toggle

