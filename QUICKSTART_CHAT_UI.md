# Quick Start - Chat UI

Minimal guide to get the chat UI running.

## Install & Run (Local)

```powershell
# 1. Install frontend dependencies
cd apps\website
pnpm install

# 2. Run frontend dev server
pnpm dev:miniapp

# 3. In new terminal, run API (or use Docker)
cd apps\api
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 4. Access chat
# Open: http://127.0.0.1:5173/miniapp/chat
```

## Install & Run (Docker)

```powershell
# From repo root
cd infra\compose

# Build & start
docker compose build api website --no-cache
docker compose up -d

# Access chat
# Open: http://localhost/miniapp/chat (adjust port/domain as configured)
```

## Test API Directly

```powershell
curl -X POST http://localhost:8000/api/chat/stub `
  -H "Content-Type: application/json" `
  -d '{"message":"hello","history":[]}'
```

Expected response:
```json
{"reply":"Hi there! I can echo and give simple hints."}
```

## Troubleshooting

**Can't reach API from frontend?**
- Set `PUBLIC_API_BASE_URL` in `apps/website/.env`
- Or temporarily set `ALLOW_DEV_CORS=1` for API

**Chat page blank?**
- Run `pnpm install` in `apps/website`
- Check browser console for errors
- Verify React integration loaded

**Bottom bar overlaps content on mobile?**
- Check viewport meta has `viewport-fit=cover`
- Test on real device, not just browser devtools

## What Was Added

- React chat widget at `/miniapp/chat`
- Stub API endpoint at `/api/chat/stub`
- Auto-resizing input, scrollable history
- Mobile-safe UI with safe-area support
- Works in Telegram Mini App webview

## Next Steps

- Connect to real AI/LLM service
- Add message persistence
- Customize styling in `ChatWidget.tsx`
- Deploy to production

---

See `CHAT_UI_IMPLEMENTATION.md` for full documentation.

