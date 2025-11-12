# Telegram Export Fix Summary

## Changes Made

### 1. Updated `apps/miniapp-api/app/services/telegram.py`

**Added features:**
- **Env fallbacks**: Added support for `TELEGRAM_ADMIN_CHAT_ID` (backward compatibility with `ADMIN_CHAT_ID`)
- **Chunking**: Implemented `_chunk_text()` function to split long messages at 4096 chars respecting line boundaries
- **sendDocument fallback**: For transcripts > 3500 chars, automatically uses `sendDocument` to send as `.txt` file
- **Improved error handling**: Added `_tg_api()` helper method with proper error handling
- **Selftest method**: Added `selftest()` method to test bot token connectivity via `getMe` API

**Key changes:**
- Line 63: Added fallback for `TELEGRAM_ADMIN_CHAT_ID`
- Lines 43-56: Added `_chunk_text()` function
- Lines 74-93: Added `_tg_api()` helper with file upload support
- Lines 95-100: Added `selftest()` method
- Lines 121-149: Updated `send()` method to handle chunking and sendDocument fallback

### 2. Updated `apps/miniapp-api/routers/chat_v2.py`

**Added endpoint:**
- `GET /api/telegram/selftest` - Tests Telegram bot token connectivity

**Improved error handling:**
- Updated `/api/export/telegram` to return proper JSON error responses
- Changed error status codes: 400 for missing config, 502 for API failures
- Better error messages indicating which env variable is missing

**Key changes:**
- Lines 132-149: Added `telegram_selftest()` endpoint
- Lines 152-194: Updated `export_telegram()` with improved error handling

## Environment Variables

**Required:**
- `TELEGRAM_TOKEN` (or `TELEGRAM_BOT_TOKEN` for backward compatibility)
- `ADMIN_CHAT_ID` (or `TELEGRAM_ADMIN_CHAT_ID` for backward compatibility)

**Optional:**
- `TELEGRAM_TIMEOUT` (default: 15.0 seconds)

## API Endpoints

### GET /api/telegram/selftest
Tests Telegram bot token. Returns bot info if token is valid.

**Response:**
```json
{
  "ok": true,
  "bot": {
    "id": 123456789,
    "is_bot": true,
    "first_name": "Bot Name",
    "username": "bot_username"
  }
}
```

### POST /api/export/telegram
Exports conversation to Telegram. Automatically handles chunking and large file fallback.

**Small transcripts (≤3500 chars):**
```json
{
  "ok": true,
  "sent": {
    "method": "sendMessage",
    "parts": 1
  }
}
```

**Large transcripts (>3500 chars):**
```json
{
  "ok": true,
  "message_id": 12345,
  "sent": {
    "method": "sendDocument"
  }
}
```

## Testing

See `TELEGRAM_EXPORT_RUNBOOK.md` for detailed testing instructions.

## Notes

- The implementation uses the existing async/httpx architecture (not synchronous requests as shown in the original diff)
- Routes are organized in `routers/chat_v2.py` rather than directly in `main.py` (following existing codebase structure)
- All error responses are JSON with appropriate HTTP status codes
- Frontend requires no changes - it already calls `/api/export/telegram`

