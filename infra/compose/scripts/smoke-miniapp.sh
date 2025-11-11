#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILES=(
  -f miniapp.compose.yaml
  -f miniapp.build.yml
  -f miniapp.runtime.yml
)

echo "[smoke] Bringing up miniapp stack..."
docker compose "${COMPOSE_FILES[@]}" up -d --wait web api

cleanup() {
  echo "[smoke] Tearing down miniapp stack..."
  docker compose "${COMPOSE_FILES[@]}" down --remove-orphans
}
trap cleanup EXIT

exec_web() {
  docker compose "${COMPOSE_FILES[@]}" exec -T web sh -lc "$1"
}

echo "[1/4] GET / via web container"
exec_web 'wget -S -O- http://127.0.0.1:8080/ | head -n 10'

echo "[2/4] GET /api/healthz via web container"
exec_web 'wget -S -O- http://127.0.0.1:8080/api/healthz'

echo "[3/4] POST /api/ask via web container"
exec_web 'wget -S -O- --header="content-type: application/json" --post-data='\''{"messages":[{"role":"user","content":"ping"}]}'\'' http://127.0.0.1:8080/api/ask'

echo "[4/4] POST /api/export/telegram?dryRun=true via web container"
exec_web 'wget -S -O- --header="content-type: application/json" --post-data='\''{"title":"smoke","messages":[{"role":"user","content":"test"}]}'\'' "http://127.0.0.1:8080/api/export/telegram?dryRun=true"'

echo "[smoke] All checks passed."
