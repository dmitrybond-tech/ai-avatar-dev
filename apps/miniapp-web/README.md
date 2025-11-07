# MiniApp Web

Local dev:

```
# in apps/miniapp-web
pnpm install
pnpm dev
```

Build locally (Vite) and preview:

```
# from repo root, respecting your package manager
pnpm install --frozen-lockfile
pnpm --filter ./apps/miniapp-web build

# or inside the app
cd apps/miniapp-web
pnpm install --frozen-lockfile
pnpm build
pnpm preview
```

Docker build (nginx serving on port 8080):

```
# from repo root so workspaces are available
docker build -f apps/miniapp-web/Dockerfile -t miniapp-web:local .
docker run --rm -p 8080:8080 miniapp-web:local
# open http://localhost:8080
```

Notes:
- API base defaults to same-origin via `src/lib/apiBase.ts`.
- Optionally set `VITE_API_BASE_URL` at build-time; empty means same-origin.
- Telegram init runs on first render via `src/lib/tg.ts`.
- Static assets emitted to `/assets/` with long caching; SPA routes fallback to `index.html`.
- **How to tweak the modal gap (60px→70px):** change the `60px` inside `--modal-top-offset` in `src/index.css` (keep the `env(safe-area-inset-top, 0px)` part); every dialog uses the shared `modal-offset-*` utilities so the new gap applies automatically.
