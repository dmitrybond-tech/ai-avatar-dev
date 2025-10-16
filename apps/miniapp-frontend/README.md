# Mini App Frontend

Single-page Astro application for the Telegram Mini App chat interface.

## Overview

This is a minimal, self-contained chat UI at `/miniapp/` that:
- Displays a conversational interface
- Sends user queries to the gateway API
- Shows structured responses (skill level, examples, booking link)
- Works as a Telegram Mini App WebApp

## Location

The Mini App page is integrated into the existing Astro website at:
```
apps/website/src/pages/miniapp/index.astro
```

This keeps the codebase DRY by reusing the existing Astro infrastructure.

## Configuration

Create or edit `apps/website/.env`:

```env
PUBLIC_GATEWAY_URL=http://localhost:8080
```

**Note:** The `PUBLIC_` prefix makes this variable available in the browser.

## Development

```bash
# Navigate to website directory
cd apps/website

# Install dependencies (if not already done)
pnpm install

# Start dev server
pnpm dev

# Visit http://localhost:5173/miniapp/
```

The Astro dev server runs on port 5173 by default (configured in `astro.config.mjs` to use port 3000, but Mini App should work on any port).

## Production Build

```bash
cd apps/website
pnpm build

# Output will be in apps/website/dist/
# Serve with any static file server
```

## Usage Flow

1. User taps "Open Assistant" button in Telegram bot
2. Telegram opens `/miniapp/` in WebApp
3. User types a query (e.g., "Python", "React", "DevOps")
4. App sends POST request to `${PUBLIC_GATEWAY_URL}/reply`
5. Gateway performs fuzzy match on Notion DB
6. App displays structured response:
   - Verdict (skill + level + years)
   - Examples (if available)
   - Booking link (if configured)

## Architecture

```
┌─────────────────┐
│  Telegram Bot   │
│   (/start)      │
└────────┬────────┘
         │ WebApp URL
         ▼
┌─────────────────┐      ┌──────────────────┐      ┌─────────────┐
│  Mini App Page  │─────▶│  Gateway API     │─────▶│  Notion DB  │
│  /miniapp/      │ POST │  /reply          │ fetch│  (Skills)   │
│  (Astro)        │◀─────│  /refresh        │◀─────│             │
└─────────────────┘ JSON └──────────────────┘      └─────────────┘
```

## Telegram Mini App Integration

### Setting Up Mini App URL

1. Talk to [@BotFather](https://t.me/BotFather)
2. Send `/mybots`
3. Choose your bot
4. Select "Bot Settings" → "Menu Button"
5. Choose "Edit URL"
6. Enter your WebApp URL: `https://yourdomain.com/miniapp/`

**Local Testing:**
- Use ngrok or cloudflare tunnel to expose localhost
- Example: `ngrok http 5173` → use the HTTPS URL provided

### Requirements for Telegram WebApp

- Must be served over HTTPS (Telegram requirement)
- URL must be publicly accessible
- For local dev, use tunneling service (ngrok, cloudflare tunnel, etc.)

## Styling

The page uses:
- Modern gradient design matching AI Avatar theme
- Responsive layout for mobile (primary Telegram use case)
- Smooth animations for message rendering
- Clean, minimal UI (KISS principle)

## Future Enhancements

When migrating to Rasa:
1. Update `PUBLIC_GATEWAY_URL` to point to Rasa REST API
2. Adjust request/response format if needed
3. No other changes required (UI stays the same)

The Mini App frontend is decoupled from the backend implementation, making the Rasa migration seamless.

