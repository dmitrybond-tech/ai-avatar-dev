# MiniApp deployment (compose runtime)

Prereqs:
- Docker and Docker Compose V2 on the VPS
- GHCR access via `docker login ghcr.io` or GitHub Actions runner

Steps:
1) Copy env template and edit values (do NOT commit secrets):
```bash
cd infra/compose
cp env.miniapp.example .env.miniapp
# Edit .env.miniapp to set WEB_* and API_* ports/tags (already prefilled)
```

2) Pull and run using runtime compose file with the env-file:
```bash
cd infra/compose
# login if needed: echo $GHCR_PAT | docker login ghcr.io -u USERNAME --password-stdin
DOCKER_BUILDKIT=1 docker compose \
  --env-file .env.miniapp \
  -f miniapp.compose.yaml -f miniapp.runtime.yml \
  up -d
```

**Note:** To force CSV source for skills (instead of Notion), add the CSV override:
```bash
DOCKER_BUILDKIT=1 docker compose \
  --env-file .env.miniapp \
  -f miniapp.compose.yaml -f miniapp.runtime.yml \
  -f miniapp.csv.override.yml \
  up -d
```

This sets `SKILLS_SOURCE=csv` and mounts `apps/miniapp-api/data/skills.csv` into the API container.

3) Check services and health:
```bash
docker compose --env-file .env.miniapp -f miniapp.compose.yaml -f miniapp.runtime.yml ps
docker compose --env-file .env.miniapp -f miniapp.compose.yaml -f miniapp.runtime.yml logs -f --tail=100
```

4) Smoke test locally on VPS:
```bash
../scripts/smoke-miniapp.sh
```

5) Optional: probe services from inside the containers (use the same compose flags as above):
```bash
docker compose --env-file .env.miniapp -f miniapp.compose.yaml -f miniapp.runtime.yml exec -T web \
  wget -qO- http://api:8000/api/healthz
docker compose --env-file .env.miniapp -f miniapp.compose.yaml -f miniapp.runtime.yml exec -T api \
  curl -sSf http://127.0.0.1:8000/api/healthz
```

Notes:
- Web publishes exactly `${WEB_HOST}:${WEB_HOST_PORT}:${WEB_CONTAINER_PORT}` (e.g. 127.0.0.1:15173:8080)
- API is internal-only (no host port); access it via the web proxy on `/api/*`
- Bot publishes no ports
- No dev ports like 5173 are published in production

