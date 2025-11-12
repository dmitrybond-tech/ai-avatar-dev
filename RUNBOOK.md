## Miniapp Deployment Runbook

- **Prerequisites**
  - Docker Engine 24+ with Compose v2 plugin (`docker compose version`).
  - Access to the VPS where Caddy terminates TLS for `miniapp.dmitrybond.tech` and `api-miniapp.dmitrybond.tech`.
  - Credentials for GHCR and the secrets listed in `infra/compose/env.miniapp.example`.

- **Initial setup**
  - Copy `infra/compose/env.miniapp.example` to `infra/compose/.env.miniapp` and fill in all required values (`TELEGRAM_TOKEN`, Notion database IDs, `IMAGE_TAG`, etc.).
  - Export a GHCR token if you need to pull private images:
    - PowerShell: `setx DOCKER_CONFIG $env:USERPROFILE\.docker`
    - Linux/macOS: `export DOCKER_CONFIG=$HOME/.docker`
    - Then run `echo "<TOKEN>" | docker login ghcr.io -u <USERNAME> --password-stdin`.

- **Deploy or update the stack**
  - Pull the latest images: `./scripts/run-miniapp.sh pull`
  - Start (or converge) services: `./scripts/run-miniapp.sh up`
    - Adds `--wait` automatically; set `MINIAPP_NO_WAIT=1` to skip.
    - Target specific services with `SERVICES="api web" ./scripts/run-miniapp.sh up`.
  - **CSV Skills Source:** To force CSV instead of Notion, always include `-f miniapp.csv.override.yml` in compose commands:
    ```bash
    # Bash
    docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml \
      -f miniapp.csv.override.yml --env-file .env.miniapp up -d
    
    # PowerShell
    docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml `
      -f miniapp.csv.override.yml --env-file .env.miniapp up -d
    ```
    This sets `SKILLS_SOURCE=csv` and mounts `apps/miniapp-api/data/skills.csv` (read-only).
    
  - **Smoke tests** (after deployment):
    ```bash
    # Bash
    curl -s "http://localhost:8000/api/skills?lang=ru" | jq '.[0] | {slug, title, short, tags}'
    curl -s "http://localhost:8000/api/skills/automation?lang=ru" | jq '{slug, title, bullets, examples}'
    curl -X POST "http://localhost:8000/api/skills/ask" \
      -H "Content-Type: application/json" \
      -d '{"q":"What can you do?","lang":"ru"}' | jq '{answer, used_skills, model}'
    ```
    ```powershell
    # PowerShell
    Invoke-RestMethod -Uri "http://localhost:8000/api/skills?lang=ru" | Select-Object -First 1 | Format-List slug,title,short,tags
    Invoke-RestMethod -Uri "http://localhost:8000/api/skills/automation?lang=ru" | Format-List slug,title,bullets,examples
    Invoke-RestMethod -Uri "http://localhost:8000/api/skills/ask" -Method POST `
      -ContentType "application/json" `
      -Body '{"q":"What can you do?","lang":"ru"}' | Format-List answer,used_skills,model
    ```
  - Alternate Make targets:
    - `make pull` — wraps `run-miniapp.sh pull`
    - `make up ARGS=--build` — pass extra flags through `ARGS`
    - `make logs SERVICES=api` — follow logs for selected services
    - `make down` — stop and remove containers

- **Health verification**
  - Confirm container health: `./scripts/run-miniapp.sh ps`
  - From the web container: `./scripts/run-miniapp.sh exec web curl -fsS http://api:8000/api/healthz`
  - From the host (after Caddy reload): `curl -I https://miniapp.dmitrybond.tech` and `curl -I https://api-miniapp.dmitrybond.tech/api/healthz`
  - Browser sanity check: open `https://miniapp.dmitrybond.tech` and ensure SPA fallback works.

- **Troubleshooting**
  - `./scripts/run-miniapp.sh logs` (or `logs SERVICES=api`) to inspect startup issues.
  - If health checks fail, verify `infra/compose/.env.miniapp` values and that GHCR images exist for both `main` and `sha-*` tags.
  - For bot/API connectivity issues, run `./scripts/run-miniapp.sh exec bot python -c "import os,urllib.request;print(urllib.request.urlopen(os.getenv('API_BASE_URL','http://api:8000') + '/api/healthz').read())"`.
  - Ensure Caddy is proxying to `127.0.0.1:15173` (web) and `127.0.0.1:18080` (api); compare with `infra/caddy/miniapp.caddy.inc`.
  - Re-render the merged configuration for debugging: `./scripts/run-miniapp.sh config`.

