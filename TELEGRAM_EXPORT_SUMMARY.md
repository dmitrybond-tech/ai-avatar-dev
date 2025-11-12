# Telegram Export Flow - Implementation Summary

## Overview

Fixed the "Finish & send to Telegram" flow to work end-to-end with proper payload handling, error management, and UI feedback.

## Changes Made

### Frontend (`apps/miniapp-web`)

1. **Chat Component** (`src/components/Chat.tsx`)
   - Generate `conv_id` using pattern: `miniapp-<ISO_DATETIME>-<6rand>`
   - Include `conv_id` and `lang` at top level of export payload
   - Button already properly disabled during export (`exporting` state)
   - Success/failure messages displayed via `exportMessage` state

2. **Types** (`src/types.ts`)
   - Added `conv_id?: string` and `lang?: "ru" | "en"` to `ChatExportPayload`
   - Maintains backward compatibility with existing `meta` field

### Backend (`apps/miniapp-api`)

1. **Chat Model** (`app/models/chat.py`)
   - Added `conv_id: Optional[str]` and `lang: Optional[Literal["en", "ru"]]` to `ExportRequest`
   - Maintains backward compatibility with `items`/`messages` shapes

2. **Chat Router** (`routers/chat_v2.py`)
   - Extract `lang` from top-level or `meta.lang`, default to "ru"
   - Use `conv_id` as title if provided, fallback to `title` or generate from `session_id`
   - Include `conv_id` and `lang` in meta for downstream processing
   - Error handling: 400 for missing env, 502 for Telegram API failures

### Infrastructure

- **Compose** (`infra/compose/miniapp.compose.yaml`)
  - No changes needed - env vars already correctly configured with fallbacks:
    - `TELEGRAM_TOKEN` / `TELEGRAM_BOT_TOKEN`
    - `ADMIN_CHAT_ID` / `TELEGRAM_ADMIN_CHAT_ID`

## Endpoints Verified

### GET `/api/telegram/selftest`
- ✅ Returns `{ok: true, bot: {...}}` on success
- ✅ Returns `400` with `{detail: "..."}` for missing env
- ✅ Returns `502` with `{detail: "..."}` for Telegram API failures

### POST `/api/export/telegram`
- ✅ Accepts both `{items:[...]}` and `{messages:[...]}` shapes
- ✅ Accepts `{conv_id, lang, messages: [...]}` payload
- ✅ Small payloads: chunks into ≤4096 and uses `sendMessage` (multiple parts if needed)
- ✅ Large payloads: sends as `.txt` via `sendDocument`
- ✅ Returns `200` with `{ok: true, sent: {method, parts?}}`
- ✅ Returns `400` for missing env vars
- ✅ Returns `502` for Telegram API failures with detailed error message

## UI Behavior

- ✅ Button disabled during export (`exporting` state)
- ✅ Button disabled when no user messages or export disabled
- ✅ Success message: "Отправила переписку в Telegram." / "Sent to Telegram."
- ✅ Error message: "Не получилось отправить переписку." / "Could not send transcript."
- ✅ Dev mode shows detailed error information

## Testing

See `TELEGRAM_EXPORT_RUNBOOK.md` for:
- curl/PowerShell commands for selftest
- Small transcript export test
- Large transcript export test (Python script)
- Error handling verification
- Backward compatibility tests

## Files Changed

1. `apps/miniapp-web/src/components/Chat.tsx` - Added conv_id generation and top-level lang
2. `apps/miniapp-web/src/types.ts` - Added conv_id and lang to ChatExportPayload
3. `apps/miniapp-api/app/models/chat.py` - Added conv_id and lang to ExportRequest
4. `apps/miniapp-api/routers/chat_v2.py` - Enhanced payload processing and title generation

## No Changes Required

- Compose environment variables (already correct)
- Caddy configuration
- Port mappings
- Domain/base-path
- Unrelated features

## Acceptance Criteria Met

✅ GET `/api/telegram/selftest` → 200 JSON with bot info (or 400 JSON if env missing)  
✅ POST `/api/export/telegram` with small transcript → 200 JSON `{ok:true, sent:{method:"sendMessage", parts: N>=1}}`  
✅ POST `/api/export/telegram` with large transcript → 200 JSON `{ok:true, sent:{method:"sendDocument"}}`  
✅ UI button click yields 200 in Network, admin receives transcript  
✅ No 502 for handled cases; 400 used for misconfig  
✅ No regressions to chat, skills, or SPA routing

