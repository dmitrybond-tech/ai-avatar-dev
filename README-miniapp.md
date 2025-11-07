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

## Skills Data (Notion + CSV fallback)
- `SKILLS_SOURCE=auto` (default) tries Notion first and falls back to the CSV bundled at `apps/api/data/skills.csv` when Notion is unavailable or misconfigured.
- `SKILLS_SOURCE=notion` enforces Notion only; the API responds with `503 {"error":"notion_failed"}` if it cannot read the database.
- `SKILLS_SOURCE=csv` serves the CSV directly and skips Notion entirely. Override `SKILLS_CSV_PATH` when the file lives elsewhere.
- `NOTION_TIMEOUT` controls the per-request timeout in seconds when Notion is enabled.

### Notion schema guidelines for skills
- Titles are auto-detected via `Title`, `Name`, `Skill`, or `Название` — the API also honours language-specific suffixes like `Title EN`, `Title_RU`, and `TitleRU`.
- Text fields such as `Short`, `Summary`, `Long`, or `Details` follow the same suffix logic (`base {LANG}`, `base_LANG`, `baseLANG`). Rich-text properties are flattened to plain strings.
- Bullet lists and examples are read from rich-text properties named `Bullets`, `Bullets EN`, `Examples`, etc.; every line (trimmed of bullets/dashes) becomes an array entry.
- Optional metadata (`Category`, `Domain`, `Tags`, `Level`, `Order`) is resolved if the Notion property exists (select, multi-select, or number). Missing fields simply default to `null`/`[]`.
- When renaming columns, keep the base name (e.g. `Short`) and only adjust the suffix — that way, the tolerant matcher keeps working without redeploying the backend.

### Local FastAPI dev (PowerShell)
```powershell
$env:SKILLS_SOURCE = 'csv'
$env:SKILLS_CSV_PATH = 'apps/api/data/skills.csv'
pwsh -NoProfile -File .\dev.ps1 api
```

The CSV lives in `apps/api/data/skills.csv`; keep the path relative to the repo root when running locally.

### Docker Compose
Add the overrides to your compose env file (for example `infra/compose/.env.miniapp`):

```
SKILLS_SOURCE=csv
SKILLS_CSV_PATH=/app/data/skills.csv
```

Then launch:

```bash
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml \
  --env-file infra/compose/.env.miniapp up -d
```

Set `SKILLS_SOURCE=auto` again when you want to switch back to Notion.

## Localization
- WebApp locale resolves once during startup via `src/shared/i18n/resolveLocale.ts` (order: `?lang` query → `localStorage('app.locale')` → Telegram init data → browser → `VITE_DEFAULT_LANG`). `LocaleProvider` persists the choice and `useLocale()/useI18n()` expose it to components while storing back to `localStorage('app.locale')`.
- Skills-related fetchers now call the API as `/api/skills?lang=<locale>` and include an `X-Locale` header so the backend can honour the chosen language.
- The Telegram bot keeps each user’s language in its state store and injects `?lang=<locale>` into the WebApp button URL every time keyboards are rendered, so the miniapp opens in the same language the user picked in chat.

## Locale Debugging
- Use the `/debug_menu` command in the bot to inspect the current locale and the exact WebApp URL (including the `lang` query) while still showing the two-button menu.
- When `DEBUG_SKILLS_API=true`, `GET /api/skills/_debug` returns `{ resolved_lang, source, count }` to verify how the API inferred the locale and how many skills were served.

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
- Buttons: `book`, `about`, `services`, `cases`, `