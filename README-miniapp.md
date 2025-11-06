MiniApp (Telegram WebApp + Bot + API)

Components:
- apps/miniapp-api: FastAPI serving rules and Cal links
- apps/miniapp-bot: aiogram v3 deterministic bot using rules
- apps/miniapp-web: Vite+React+TS static WebApp UI

Local development (PowerShell):
- API: `pwsh ./dev.ps1 api`
- Bot: `pwsh ./dev.ps1 bot`
- Web: `pwsh ./dev.ps1 web`

Environment examples:
- API: `apps/miniapp-api/env.example`
- Bot: `apps/miniapp-bot/env.example`
- Web: `apps/miniapp-web/env.example`
- Compose: `infra/compose/env.miniapp.example`

CI:
- `.github/workflows/miniapp-ci.yml` validates API rules, compiles bot, builds web
 - `.github/workflows/miniapp-build.yml` builds and pushes GHCR images on pushes to `main` and tags `v*`

Container images (GHCR):
- `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-api` — tags: `main`, `sha-<short>`, and `latest` on `v*`
- `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-bot` — tags: `main`, `sha-<short>`, and `latest` on `v*`
- `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-web` — tags: `main`, `sha-<short>`, and `latest` on `v*`

Deploy (VPS, docker compose):
1) DNS (Cloudflare): create A record `miniapp` -> <VPS IP> (DNS-only initially)
2) On VPS (production stack using GHCR images):
```
cd /srv/ai-avatar/infra/compose
cp env.miniapp.example .env.miniapp
docker compose -f miniapp.stack.yml --env-file .env.miniapp pull
docker compose -f miniapp.stack.yml --env-file .env.miniapp up -d
```
3) Caddy: add snippet from `infra/compose/CADDY_SNIPPETS.md` to `/etc/caddy/Caddyfile`, then:
```
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```
4) BotFather:
- `/setdomain` -> `miniapp.dmitrybond.tech`
- Menu Button -> Configure Web App -> `https://miniapp.dmitrybond.tech/`

Notes:
- WebApp calls API via the same domain (`VITE_API_BASE_URL`), CORS is open for dev
- Deterministic flows only, no RASA/LLM calls
 - Caddy proxies `miniapp.dmitrybond.tech` → `localhost:5173` (web) and `localhost:8080` (api)
 - API now mounts `skills` router at both flat paths and under `/api` from `apps.miniapp_api.main`, and the container starts via `uvicorn apps.miniapp_api.main:app`.

Skills + Tasks hardening (server):
- GET `/skills`, `/skills/{slug}` and aliases under `/api/skills/...`
- Public tasks available at `/api/tasks/public` + aliases `/api/public`, `/public`
- Unified health: `GET /healthz` → `{ "ok": true }`
- Compose final override: `infra/compose/miniapp.final.override.yml` sets NOTION_* and uvicorn CMD
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

### Reset Webhook
If the bot is not responding to `/start` commands, the webhook might be set. Reset it:

```bash
export TG_TOKEN=your_bot_token_here  # not in repo
curl -s "https://api.telegram.org/bot$TG_TOKEN/getWebhookInfo"
curl -s "https://api.telegram.org/bot$TG_TOKEN/deleteWebhook?drop_pending_updates=false"
```

### Runbook
Deploy with Docker Compose:

```bash
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml \
  --env-file infra/compose/.env.miniapp up -d --build
```

### Smoke Test
Test all endpoints:

```bash
# API health
curl -f http://127.0.0.1:8081/healthz

# API skills
curl -f "http://127.0.0.1:8081/skills?lang=ru"

## Migration: Rules → Skills

- New endpoints:
  - `GET /skills` — list of skills (supports `?lang=ru|en` to project localized fields)
  - `GET /skills/{slug}` — detail for a skill (supports `?lang=ru|en`)
- Backward-compatible aliases (kept during rollout):
  - `GET /rules` → same payload as `/skills` (200)
  - `GET /rules/{slug}` → same payload as `/skills/{slug}` (200)
- Source of truth: Notion DB referenced by `NOTION_DB_SKILLS` (if unset, uses `NOTION_DB` and accepts legacy entries with context "Rules").
- Fallback seeds: `apps/miniapp-api/seed/skills.en.json` and `skills.ru.json` are merged with Notion; Notion takes precedence.

Smoke tests (prod):

```bash
curl -sS https://miniapp.dmitrybond.tech/skills | jq '.[0]'
curl -sS https://miniapp.dmitrybond.tech/skills/automation | jq '.slug'
curl -sS https://miniapp.dmitrybond.tech/rules | jq '.[0]' # legacy alias
```

# Web app (should show fallback outside Telegram)
curl -f http://127.0.0.1:5175/
```

### Common Issues
- Telegram WebApp requires public HTTPS; for local dev use tunnels (e.g., Cloudflare Tunnel/Ngrok) and set `WEBAPP_URL`
- If Vite dev doesn't open externally, use tunnels or run `vite preview` in Compose
- CORS: API allows specific domains only (production + localhost)
- Windows: ensure Python 3.12 and Node.js 20+
- Bot not responding: check webhook status and reset if needed

## Acceptance Test (Manual)
1. Start API, then Bot, then Web locally
2. In Telegram chat:
   - `/start` shows "Привет! Открывай мини-апп 👇" with "Open Mini App" WebApp button
   - Tap WebApp button → opens Mini App UI with proper Telegram context
   - Tap "Book a call" → opens `https://cal.com/<CAL_USERNAME>/<CAL_EVENT_INTRO>`
   - Navigate About/Services/Cases → texts from YAML
   - `/healthz` replies `ok`; API `/healthz` returns `{status:"ok"}`
3. Outside Telegram (browser):
   - Open `https://miniapp.dmitrybond.tech/miniapp/` → shows "Open in Telegram" fallback
   - Click "Open in Telegram" → redirects to bot

CI: ping to trigger build-and-push-miniapp workflow.