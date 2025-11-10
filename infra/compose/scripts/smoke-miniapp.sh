#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

BASE_URL="${1:-}"

if [[ -z "${BASE_URL}" ]]; then
  WEB_HOST="127.0.0.1"
  WEB_PORT=""

  if [[ -f .env.miniapp ]]; then
    while IFS='=' read -r key value; do
      case "$key" in
        WEB_HOST) WEB_HOST="${value}" ;;
        WEB_HOST_PORT|WEB_PORT) WEB_PORT="${value}" ;;
      esac
    done < <(grep -E '^(WEB_HOST|WEB_HOST_PORT|WEB_PORT)=' .env.miniapp || true)
  fi

  WEB_PORT="${WEB_PORT:-15173}"
  BASE_URL="http://${WEB_HOST}:${WEB_PORT}"
fi

if [[ "${BASE_URL}" != http* ]]; then
  BASE_URL="http://${BASE_URL}"
fi

echo "[1/4] Web root check ${BASE_URL}/"
code=$(curl -ksS -o /dev/null -w "%{http_code}" "${BASE_URL}/")
if [[ "$code" != "200" ]]; then
  echo "Expected 200, got $code"
  exit 1
fi

echo "[2/4] First asset HEAD 200"
asset=$(curl -ksS "${BASE_URL}/" | grep -oE "/assets/[^\"']+" | head -n1 || true)
if [[ -z "${asset}" ]]; then
  echo "No asset found on index page"
  exit 1
fi
code=$(curl -ksSI -o /dev/null -w "%{http_code}" "${BASE_URL}${asset}")
if [[ "$code" != "200" ]]; then
  echo "Asset ${asset} not 200, got $code"
  exit 1
fi

echo "[3/4] API healthz via web proxy ${BASE_URL}/api/healthz"
code=$(curl -ksS -o /dev/null -w "%{http_code}" "${BASE_URL}/api/healthz")
if [[ "$code" != "200" ]]; then
  echo "API /api/healthz expected 200, got $code"
  exit 1
fi

echo "[4/4] POST /api/ask smoke"
payload='{"messages":[{"role":"user","content":"ping"}],"lang":"en"}'
response="$(curl -ksS -w '\n%{http_code}' -H "content-type: application/json" -d "${payload}" "${BASE_URL}/api/ask")"
body="${response%$'\n'*}"
status="${response##*$'\n'}"
if [[ "$status" != "200" ]]; then
  echo "Expected 200 from /api/ask, got $status"
  echo "Body: $body"
  exit 1
fi

if command -v jq >/dev/null 2>&1; then
  answer=$(echo "$body" | jq -r '.answer // empty')
else
  answer=$(echo "$body" | grep -o '"answer"\s*:\s*"[^"]*"' | head -n1 | sed 's/^.*"answer"\s*:\s*"\(.*\)"$/\1/')
fi

if [[ -z "${answer}" ]]; then
  echo "Smoke request succeeded but response lacks answer field"
  echo "Body: $body"
  exit 1
fi

echo "Smoke OK — ${BASE_URL}"

