#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

COMPOSE_FILES=(
  -f miniapp.compose.yaml
  -f miniapp.runtime.yml
  -f miniapp.stack.yml
  -f miniapp.notion.override.yml
  -f miniapp.final.override.yml
)

usage() {
  cat <<'USAGE'
Usage: miniapp.sh <command> [args...]

Commands:
  up [services...]       Start services with env wired
  down [args...]         Stop services
  logs [args...]         Tail logs
  ps [args...]           Show service status
  config                 Render composed config
  exec [args...]         Execute commands in containers
USAGE
}

run_compose() {
  docker compose "${COMPOSE_FILES[@]}" "$@"
}

case "${1:-}" in
  up)
    shift || true
    run_compose --env-file .env.miniapp up -d "$@"
    ;;
  down)
    shift || true
    run_compose --env-file .env.miniapp down "$@"
    ;;
  logs)
    shift || true
    run_compose --env-file .env.miniapp logs -f "$@"
    ;;
  ps)
    shift || true
    run_compose --env-file .env.miniapp ps "$@"
    ;;
  config)
    shift || true
    run_compose --env-file .env.miniapp config "$@"
    ;;
  exec)
    shift || true
    run_compose --env-file .env.miniapp exec "$@"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

