# Telegram Mini App — Rule-Based Personal Assistant (RU/EN)

This mini app is a deterministic, rule-based assistant that:
- Books meetings via Cal.com (WebApp button + deep links)
- Provides concise info about the owner (bio, services, cases, stack) using scripted flows
- Supports RU/EN i18n loaded from YAML

Monorepo path: `C:\PersonalProjects\ai-avatar`

## Components
- `apps/miniapp-api` — FastAPI serving `/healthz`, `/rules`, `/cal/suggest`
- `apps/miniapp-bot` — Telegram bot (aiogram v3), scenes + i18n, `/healthz`
- `apps/miniapp-web` — Telegram WebApp (Vite + React + TS + Tailwind)

All content and i18n are declared in `apps/miniapp-api/rules.yaml`.

## Env Examples
Create `.env` files per app with the following keys:

API (`apps/miniapp-api/.env`):
```
PORT=8080
CAL_USERNAME=dmitrybond
CAL_HOST=cal.com
DEFAULT_LANG=ru
```

Bot (`apps/miniapp-bot/.env`):
```
TELEGRAM_TOKEN=
TELEGRAM_BOT_NAME=
API_BASE_URL=http://127.0.0.1:8080
DEFAULT_LANG=ru
CAL_USERNAME=dmitrybond
CAL_EVENT_INTRO=intro-30m
# Optional for local testing; set to public https URL in production
WEBAPP_URL=http://127.0.0.1:5173
```

Web (`apps/miniapp-web/.env`):
```
VITE_API_BASE_URL=http://127.0.0.1:8080
VITE_DEFAULT_LANG=ru
```

> Never commit secrets. Use `.env` locally and CI/CD secrets in production.

## Dev (Windows / PowerShell)
From repo root:

- Start API:
```
pwsh -NoProfile -File .\dev.ps1 api
```
- Start Bot:
```
pwsh -NoProfile -File .\dev.ps1 bot
```
- Start Web (Vite dev server):
```
pwsh -NoProfile -File .\dev.ps1 web
```

## Optional: Docker Compose
A simple compose file is provided:
```
docker compose -f infra/compose/miniapp.compose.yaml up -d
```
- API: `http://127.0.0.1:8080/healthz`
- Web: `http://127.0.0.1:5173/`

## BotFather Setup
1. Create bot: `/newbot` → set Name and Username
2. Set WebApp: Menu Button → Configure Web App → set URL to hosted `miniapp-web`
3. (If needed) `/setdomain` for the Mini App host
4. Deep link examples (startapp):
   - `https://t.me/<YOUR_BOT_USERNAME>?startapp=book`

## Flows & i18n
- YAML lives in `apps/miniapp-api/rules.yaml`
- Scenes: `start`, `about`, `services`, `cases`
- Buttons: `book`, `about`, `services`, `cases`, `start`, `back`, `language`
- API `/rules?lang=ru|en` returns language-projected JSON

## Booking
- Bot: "Book a call" sends WebApp button and a Cal.com deep link fallback
- Web: Book button calls `/cal/suggest` then opens URL in external browser

## Health & Reliability
- API `GET /healthz` → `{ "status": "ok" }`
- Bot `/healthz` → `ok`
- Timeouts/retries for API calls in bot via `httpx`

## Troubleshooting
- Telegram WebApp requires public HTTPS; for local dev use tunnels (e.g., Cloudflare Tunnel/Ngrok) and set `WEBAPP_URL`
- If Vite dev doesn’t open externally, use tunnels or run `vite preview` in Compose
- CORS: API allows `*` for local dev only
- Windows: ensure Python 3.12 and Node.js 20+

## Acceptance Test (Manual)
1. Start API, then Bot, then Web locally
2. In Telegram chat:
   - `/start` shows buttons and language toggle
   - Tap WebApp button → opens Mini App UI
   - Tap "Book a call" → opens `https://cal.com/<CAL_USERNAME>/<CAL_EVENT_INTRO>`
   - Navigate About/Services/Cases → texts from YAML
   - `/healthz` replies `ok`; API `/healthz` returns `{status:"ok"}`
