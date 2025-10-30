# MiniApp Web

Local dev:

```
# in apps/miniapp-web
pnpm install
pnpm dev
```

Notes:
- API base defaults to same-origin via `src/lib/apiBase.ts`.
- Optionally set `VITE_API_BASE_URL` at build-time; empty means same-origin.
- Telegram init runs on first render via `src/lib/tg.ts`.
