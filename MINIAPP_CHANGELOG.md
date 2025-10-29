# MiniApp Change Log

1. Added `apps/miniapp-api` service
   - `requirements.txt` pinned
   - `main.py` with `GET /healthz`, `GET /rules`, `GET /cal/suggest`
   - `rules.yaml` declarative i18n, intents, scenes, labels
   - `.env` keys documented in README
2. Added `apps/miniapp-bot` service
   - `requirements.txt` pinned
   - `main.py` aiogram v3 bot with `/start`, `/healthz`, scenes, language toggle, WebApp button, Cal.com fallback
   - `.env` keys documented in README
3. Added `apps/miniapp-web` Telegram WebApp
   - Vite + React + TS + Tailwind setup with pinned deps
   - `index.html`, `vite.config.ts`, `tsconfig.json`, `postcss.config.js`, `tailwind.config.js`
   - `src/` with `App.tsx`, `main.tsx`, `index.css`, `vite-env.d.ts`
   - Fetches `/rules`, renders four buttons, language toggle, opens Cal URL
   - `.env` keys documented in README
4. Added `dev.ps1` PowerShell helper for Windows-first dev
   - `bot`, `api`, `web` commands
5. Added optional Docker Compose
   - `infra/compose/miniapp.compose.yaml` for `api`, `bot`, `web`
6. Added documentation
   - `README-miniapp.md` with setup, BotFather notes, troubleshooting
