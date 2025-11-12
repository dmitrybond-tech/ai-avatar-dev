# Root Cause Analysis: Telegram Export Flow

## Issues Identified

1. **Frontend payload shape mismatch** (`apps/miniapp-web/src/components/Chat.tsx:319-327`)
   - Frontend was sending `{messages: [...], meta: {lang, ...}}` 
   - Requirements specify `{conv_id, lang, messages: [...]}` at top level
   - Missing `conv_id` generation and top-level `lang` field

2. **Backend model incomplete** (`apps/miniapp-api/app/models/chat.py:37-43`)
   - `ExportRequest` model didn't accept `conv_id` or `lang` at top level
   - Backend could handle `messages` vs `items` but couldn't extract `conv_id` or top-level `lang`

3. **Title generation** (`apps/miniapp-api/routers/chat_v2.py:179`)
   - Backend wasn't using `conv_id` as title when provided
   - Title fallback logic needed improvement

## Why 502 Happened

- Backend error handling was correct (returns 502 for Telegram API failures, 400 for missing env)
- The issue was likely payload shape mismatch causing validation errors or missing context
- Frontend wasn't generating `conv_id`, so transcripts couldn't be uniquely identified

## Why History Wasn't Exported

- Frontend button handler (`finishAndSend`) was calling the API correctly
- Payload shape didn't match expected format, potentially causing backend to reject or mishandle the request
- Missing `conv_id` meant transcripts couldn't be properly titled/identified in Telegram

## Fixes Applied

1. **Frontend** (`apps/miniapp-web/src/components/Chat.tsx:319-333`)
   - Generate `conv_id` using pattern: `miniapp-<ISO_DATETIME>-<6rand>`
   - Include `conv_id` and `lang` at top level of payload
   - Keep backward compatibility with `meta` field

2. **Backend Model** (`apps/miniapp-api/app/models/chat.py:37-43`)
   - Added optional `conv_id` and `lang` fields to `ExportRequest`
   - Maintains backward compatibility with existing `items`/`messages` shapes

3. **Backend Handler** (`apps/miniapp-api/routers/chat_v2.py:171-191`)
   - Extract `lang` from top-level or `meta.lang`, default to "ru"
   - Use `conv_id` as title if provided, fallback to `title` or generate from `session_id`
   - Include `conv_id` and `lang` in meta for downstream processing

## Verification

- ✅ GET `/api/telegram/selftest` exists and returns proper JSON (400/502)
- ✅ POST `/api/export/telegram` accepts both `{items:[...]}` and `{messages:[...]}`
- ✅ Error handling: 400 for missing env, 502 for Telegram API failures
- ✅ Compose env vars correctly set with fallbacks (`TELEGRAM_TOKEN`, `ADMIN_CHAT_ID`)

