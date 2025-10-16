# Chat UI Implementation - Deliverable

## Change Log (Numbered)

1. **Astro React Integration** — Enabled `@astrojs/react` in `astro.config.mjs` and added pinned React dependencies (`@astrojs/react@3.6.2`, `react@18.3.1`, `react-dom@18.3.1`) plus TypeScript types in `package.json`.

2. **Chat UI Component** — Added React island `ChatWidget.tsx` with:
   - Scrollable message history with auto-scroll on new messages
   - Sticky full-width bottom input bar with safe-area padding
   - Auto-resizing textarea (Enter to send, Shift+Enter for newline)
   - Loading state during API calls
   - Fallback error handling with local message
   - Fetch to `POST /api/chat/stub` endpoint
   - Mobile-friendly styling with `100dvh`, touch-action, and safe-area insets

3. **Chat Page** — Created `pages/miniapp/chat.astro` hosting the ChatWidget component with proper viewport meta tags for Telegram Mini App webview compatibility.

4. **API Stub Router** — Added FastAPI router `chat_stub.py` with:
   - `POST /api/chat/stub` endpoint
   - Request body: `{ message: str, history?: [{ role: "user"|"assistant", text: str }] }`
   - Response: `{ reply: str }`
   - Rule-based reply logic (greetings, help, echo)
   - No database dependencies

5. **Router Registration** — Registered `chat_stub` router in `main.py` and added optional dev CORS (gated by `ALLOW_DEV_CORS=1` environment variable).

## Files Created

- `apps/website/src/components/ChatWidget.tsx`
- `apps/website/src/pages/miniapp/chat.astro`
- `apps/api/src/app/adapters/web/chat_stub.py`

## Files Modified

- `apps/website/astro.config.mjs` — Added React integration
- `apps/website/package.json` — Added React dependencies
- `apps/api/src/app/main.py` — Imported and registered chat_stub router, added dev CORS

## Runbook (PowerShell)

### Prerequisites

- Node.js/pnpm installed
- Python 3.11+ for API
- Docker + Docker Compose (for containerized deployment)

### Local Development Setup

```powershell
# Navigate to repository root
cd C:\PersonalProjects\ai-avatar

# 1. Install frontend dependencies
cd apps\website
pnpm install

# 2. Run Astro dev server (if testing frontend only)
pnpm dev:miniapp
# Frontend will be at: http://127.0.0.1:5173/miniapp/

# 3. In a separate terminal, run the API (if not using Docker)
cd ..\..\apps\api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main
# API will be at: http://localhost:8000

# 4. Test the stub endpoint
curl -X POST http://localhost:8000/api/chat/stub `
  -H "Content-Type: application/json" `
  -d '{"message": "hello", "history": []}'
```

### Docker Compose Deployment

```powershell
# From repository root
cd infra\compose

# Build updated services
docker compose -f docker-compose.yml build api website --no-cache

# Start services
docker compose -f docker-compose.yml up -d

# Check logs
docker compose -f docker-compose.yml logs -f api
docker compose -f docker-compose.yml logs -f website

# Test the API endpoint (adjust port if needed)
curl -X POST http://localhost:8000/api/chat/stub `
  -H "Content-Type: application/json" `
  -d '{"message": "hi", "history": []}'
```

### Access the Chat Page

1. **Local dev**: Navigate to `http://127.0.0.1:5173/miniapp/chat`
2. **Production**: Navigate to `https://your-domain.com/miniapp/chat`
3. **Telegram Mini App**: The page works in Telegram webview with proper safe-area handling

### Environment Variables

#### Frontend (Optional)

If `/api` is not proxied to the backend from your frontend host, set:

```
PUBLIC_API_BASE_URL=https://your-api-host.com
```

Create `apps/website/.env`:
```
PUBLIC_API_BASE_URL=https://api.example.com
```

Then rebuild:
```powershell
cd apps\website
pnpm build:miniapp
```

The widget will use `{PUBLIC_API_BASE_URL}/api/chat/stub`.

#### Backend (Optional)

To enable permissive CORS for local development:

```
ALLOW_DEV_CORS=1
```

Add to your `.env` file or Docker Compose environment:
```yaml
services:
  api:
    environment:
      - ALLOW_DEV_CORS=1
```

**Warning**: Only use `ALLOW_DEV_CORS=1` in local development, never in production.

## Testing Checklist

- [ ] GET `/miniapp/chat` renders the chat UI
- [ ] Bottom input bar is full width, sticky, and respects safe-area on mobile
- [ ] Message list fills remaining height and scrolls independently
- [ ] Auto-scroll works on new messages
- [ ] Enter key sends message, Shift+Enter inserts newline
- [ ] Input/button disabled state during API call
- [ ] Loading indicator shows while waiting for response
- [ ] POST `/api/chat/stub` returns rule-based reply
- [ ] UI displays API response correctly
- [ ] On network error, fallback message is displayed
- [ ] No database queries are made
- [ ] Works in Telegram Mini App webview
- [ ] Works in standard mobile browsers (Chrome, Safari)

## API Contract

### POST /api/chat/stub

**Request:**
```json
{
  "message": "Hello",
  "history": [
    { "role": "user", "text": "Hi" },
    { "role": "assistant", "text": "Hello!" }
  ]
}
```

**Response:**
```json
{
  "reply": "Hi there! I can echo and give simple hints."
}
```

**Rule-Based Logic:**
- Detects greetings (hi, hello, hey, etc.) → Returns friendly greeting
- Detects help requests (help, how, what can you do) → Returns capability description
- Otherwise → Echoes user message with a prefix

## Troubleshooting

### Frontend can't reach API

**Symptom**: Chat shows "Local fallback: I couldn't reach the API..."

**Solution**: 
1. Check if API is running: `curl http://localhost:8000/api/chat/stub`
2. If using separate hosts, set `PUBLIC_API_BASE_URL` in frontend `.env`
3. Verify CORS settings in `apps/api/src/app/main.py`
4. For dev, try setting `ALLOW_DEV_CORS=1` temporarily

### Chat page is blank

**Symptom**: White screen at `/miniapp/chat`

**Solution**:
1. Check browser console for errors
2. Ensure React integration is loaded: `pnpm install` was run
3. Verify `ChatWidget.tsx` imports correctly
4. Check Astro build logs: `pnpm dev:miniapp`

### Textarea not resizing

**Symptom**: Textarea stays single line

**Solution**: This is expected - textarea auto-resizes as you type. Type multiple lines to see it expand.

### Safe-area not working on iOS

**Symptom**: Bottom bar overlaps iPhone notch/home indicator

**Solution**: 
1. Ensure viewport meta includes `viewport-fit=cover`
2. Check `env(safe-area-inset-bottom)` is applied
3. Test in actual device, not simulator

## Architecture Notes

### Why a separate stub endpoint?

- Existing `/chat` endpoint uses database and full chat service
- Stub endpoint provides quick testing without DB dependencies
- Useful for frontend development and demo purposes
- Can be extended with more sophisticated rule-based logic if needed

### Mobile responsiveness

- Uses `100dvh` for dynamic viewport height (handles mobile address bar)
- Safe-area insets prevent content from being obscured by notches/home indicators
- Touch-action manipulation prevents double-tap zoom
- Sticky bottom bar with backdrop blur for modern native-like feel
- WebKit overflow scrolling for smooth iOS scrolling

### No Tailwind dependency

- Project doesn't use Tailwind CSS
- Component uses inline React styles for portability
- Styles are scoped to component, no global CSS pollution
- Easy to customize colors/spacing by editing ChatWidget.tsx

## Future Enhancements (Not Implemented)

These are potential improvements but not part of current deliverable:

- [ ] Connect to actual LLM/AI service
- [ ] Add message timestamps
- [ ] Add typing indicators (animated dots)
- [ ] Add message status (sent, delivered, read)
- [ ] Add file/image upload
- [ ] Add voice message support
- [ ] Persist chat history to localStorage
- [ ] Add user avatars
- [ ] Add markdown rendering in messages
- [ ] Add emoji picker
- [ ] Add dark mode toggle

---

**Implementation Date**: 2025-10-16  
**Status**: ✅ Complete  
**Tested**: Local dev environment  
**Ready for**: Staging deployment

