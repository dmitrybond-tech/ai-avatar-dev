#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
COMPOSE_DIR=$(cd -- "${SCRIPT_DIR}/../infra/compose" && pwd)

services=(web api)

if [[ "${1:-}" == "--all" ]]; then
  services=(web api bot)
fi

cd "${COMPOSE_DIR}"

compose_cmd=(
  docker compose --env-file .env.miniapp \
    -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml \
    -f miniapp.notion.override.yml -f miniapp.final.override.yml
)

"${compose_cmd[@]}" pull "${services[@]}"
"${compose_cmd[@]}" up -d "${services[@]}"

