# Miniapp Production Recovery

This runbook captures the steps to refresh, verify, and roll back the miniapp stack that powers `miniapp.dmitrybond.tech`.

## Components & Ports
- `web` (Nginx + SPA): listens on container `8080`, published on the host as `127.0.0.1:15173`. Caddy terminates TLS and proxies to this port.
- `api` (FastAPI/Uvicorn): serves on container `8000`, reachable from other containers as `http://api:8000`. Exposed for Caddy as `127.0.0.1:18080` when the secondary domain is used.
- `bot` (Telegram worker): optional, started alongside web/api once they are healthy.

All services share the default project network defined by the compose files under `infra/compose/`.

## Pre-flight Checklist
1. Ensure the target host has the latest `.env.miniapp` at `/srv/ai-avatar/infra/compose/.env.miniapp`.
2. Confirm GHCR access:
   ```bash
   docker login ghcr.io
   ```
3. Record the GHCR tags or digests you plan to deploy (usually `:main` plus an immutable `<shortsha>-<UTC>` tag produced by the CI pipeline).

## Render the Effective Configuration
Run this from the repository root (or copy to the VPS) to confirm the merged compose configuration is valid before touching running services:
```bash
docker compose \
  --env-file /srv/ai-avatar/infra/compose/.env.miniapp \
  -f infra/compose/miniapp.compose.yaml \
  -f infra/compose/miniapp.runtime.yml \
  -f infra/compose/miniapp.stack.yml \
  -f infra/compose/miniapp.notion.override.yml \
  -f infra/compose/miniapp.final.override.yml \
  -f infra/compose/miniapp.readiness.override.yml \
  config
```

## Deploy or Refresh
```bash
cd /srv/ai-avatar

docker compose \
  --env-file infra/compose/.env.miniapp \
  -f infra/compose/miniapp.compose.yaml \
  -f infra/compose/miniapp.runtime.yml \
  -f infra/compose/miniapp.stack.yml \
  -f infra/compose/miniapp.notion.override.yml \
  -f infra/compose/miniapp.final.override.yml \
  -f infra/compose/miniapp.readiness.override.yml \
  pull

docker compose \
  --env-file infra/compose/.env.miniapp \
  -f infra/compose/miniapp.compose.yaml \
  -f infra/compose/miniapp.runtime.yml \
  -f infra/compose/miniapp.stack.yml \
  -f infra/compose/miniapp.notion.override.yml \
  -f infra/compose/miniapp.final.override.yml \
  -f infra/compose/miniapp.readiness.override.yml \
  up -d --wait --remove-orphans
```
`--wait` blocks until the healthchecks for `api` and `web` pass, ensuring the SPA is only exposed when the backend is ready.

## Verification
- **Edge (through Caddy):**
  ```bash
  curl -fsSI https://miniapp.dmitrybond.tech | head -n1
  curl -fsS https://miniapp.dmitrybond.tech/api/healthz
  ```
  Expect HTML with a `Server: Caddy` header on the edge and an `ok` JSON response for `/api/healthz`.

- **From the host against the compose network:**
  ```bash
  docker compose ... exec web wget -qO- http://api:8000/api/healthz
  docker compose ... exec api wget -qO- http://127.0.0.1:8000/api/healthz
  docker compose ... exec web wget -qO- http://127.0.0.1:8080/ | head -n5
  ```
  Replace `docker compose ...` with the command bundle shown in the deploy section (omit `pull/up`).

- **Log tailing (optional):**
  ```bash
  docker compose ... logs -f api web
  ```

## Rollback
1. Identify the previous known-good tags or digests (recorded in CI summaries).
2. Export them before rerunning `pull`:
   ```bash
   export IMAGE_TAG=<previous-tag>
   # or override IMAGE_API / IMAGE_WEB with fully qualified digest references
   ```
3. Repeat the deploy sequence (`pull` + `up -d --wait`). The stack will revert to the supplied tags while keeping volumes intact.

## Troubleshooting
- **`/api/healthz` fails from the edge:** check that `web` can reach `http://api:8000/api/healthz` from inside the container. If it fails, inspect API logs for Notion errors; degraded health still returns JSON but with `"status": "degraded"`.
- **Nginx serves the SPA but API requests 502:** confirm the `web` container has the updated `/etc/nginx/conf.d/default.conf` (look for `proxy_pass http://api:8000$request_uri`). Recreate the `web` service if the config is stale.
- **Compose config complains about duplicate keys:** ensure the file list matches the order shown above; stray overrides from past incidents can reintroduce duplicate `services` keys.


