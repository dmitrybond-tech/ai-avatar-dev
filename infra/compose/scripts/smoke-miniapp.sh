#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Load ports from .env.miniapp
if [[ -f .env.miniapp ]]; then
  # shellcheck disable=SC2046
  export $(grep -E '^WEB_HOST_PORT=' .env.miniapp | xargs)
else
  echo ".env.miniapp not found in $(pwd). Exiting." >&2
  exit 1
fi

echo "[1/3] Web root check on http://127.0.0.1:${WEB_HOST_PORT}/"
code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${WEB_HOST_PORT}/")
test "$code" = "200" || { echo "Expected 200, got $code"; exit 1; }

echo "[2/3] First asset HEAD 200"
asset=$(curl -s "http://127.0.0.1:${WEB_HOST_PORT}/" | grep -oE "/assets/[^"]+" | head -n1)
test -n "$asset" || { echo "No asset found on index page"; exit 1; }
code=$(curl -s -I -o /dev/null -w "%{http_code}" "http://127.0.0.1:${WEB_HOST_PORT}${asset}")
test "$code" = "200" || { echo "Asset ${asset} not 200, got $code"; exit 1; }

echo "[3/3] API healthz via web proxy http://127.0.0.1:${WEB_HOST_PORT}/api/healthz"
code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${WEB_HOST_PORT}/api/healthz")
test "$code" = "200" || { echo "API /api/healthz expected 200, got $code"; exit 1; }

echo "Smoke OK"

