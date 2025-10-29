# Telegram Mini App Fixes - Changelog

## Overview
Fixed `/start` command reliability and Telegram Mini App loading issues. Ensured aiogram ≥3.7 compatibility, proper polling (no leftover webhook), correct handlers, WebApp button, safe CORS, and browser fallback.

## Changes Made

### Bot (apps/miniapp-bot/main.py)
- ✅ Updated to aiogram 3.7 syntax with proper imports
- ✅ Added `CommandStart` filter and `ReplyKeyboardMarkup` for WebApp button
- ✅ Simplified `/start` handler to show "Привет! Открывай мини-апп 👇" with WebApp button
- ✅ Added `BOT_MODE` environment variable (defaults to "polling")
- ✅ Added webhook cleanup on startup when in polling mode
- ✅ Added clear startup log: "BOT: polling started"
- ✅ Used `dp.resolve_used_update_types()` for efficient polling

### API (apps/miniapp-api/main.py)
- ✅ Updated CORS to allow specific domains only:
  - `https://miniapp.dmitrybond.tech` (production)
  - `http://localhost:5173` (local dev)
  - `http://127.0.0.1:5173` (local dev alternative)
- ✅ Set `allow_credentials=False` for security
- ✅ Limited methods to `["GET", "POST", "OPTIONS"]`

### Web App (apps/miniapp-web/src/App.tsx)
- ✅ Added Telegram WebApp context detection
- ✅ Added `window.Telegram?.WebApp?.ready()` call on init
- ✅ Added fallback UI for non-Telegram contexts
- ✅ Fallback shows "Open in Telegram" with link to `https://t.me/db_ai_avatar_bot/app?startapp=start`
- ✅ No infinite spinner - immediate fallback rendering

### Documentation (README-miniapp.md)
- ✅ Added "Reset Webhook" section with curl commands
- ✅ Added "Runbook" section with Docker Compose command
- ✅ Added "Smoke Test" section with endpoint testing
- ✅ Updated "Acceptance Test" to reflect new behavior
- ✅ Added troubleshooting for webhook issues

## Acceptance Criteria Met

1. ✅ `/start` command replies within 1-2s with message and "Open Mini App" WebApp button
2. ✅ Mini App loads immediately inside Telegram with proper context
3. ✅ Mini App shows immediate fallback outside Telegram (no infinite spinner)
4. ✅ `getWebhookInfo` is empty by default; bot logs show "polling started"
5. ✅ No aiogram 3.7 deprecation errors
6. ✅ API serves `/healthz` and `/rules?lang=ru` with 200 status
7. ✅ CORS preflight for `/rules` succeeds
8. ✅ README updated with webhook reset and runbook instructions

## Technical Details

### Bot Handler Structure
```python
@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    web_app = WebAppInfo(url=f"{WEBAPP_URL}/miniapp/")
    button = KeyboardButton(text="Open Mini App", web_app=web_app)
    keyboard = ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)
    await message.answer("Привет! Открывай мини-апп 👇", reply_markup=keyboard)
```

### Web App Fallback
```tsx
if (!isTelegram) {
  return (
    <div className="min-h-dvh w-full bg-white text-black flex items-center justify-center">
      <div className="max-w-md mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold mb-4">Open in Telegram</h1>
        <a href="https://t.me/db_ai_avatar_bot/app?startapp=start">
          Open in Telegram
        </a>
      </div>
    </div>
  )
}
```

### CORS Configuration
```python
allowed_origins = [
    "https://miniapp.dmitrybond.tech",  # Production
    "http://localhost:5173",            # Local dev
    "http://127.0.0.1:5173",           # Local dev alternative
]
```

## Files Modified
- `apps/miniapp-bot/main.py` - Bot implementation fixes
- `apps/miniapp-api/main.py` - CORS security improvements  
- `apps/miniapp-web/src/App.tsx` - Telegram context detection and fallback
- `README-miniapp.md` - Documentation updates

## No Breaking Changes
- ✅ No folder structure changes
- ✅ No service name changes
- ✅ No Caddy routing changes
- ✅ No secrets leaked
- ✅ Backward compatible with existing setup
