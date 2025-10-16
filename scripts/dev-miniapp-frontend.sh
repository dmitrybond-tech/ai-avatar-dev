#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PUBLIC_GATEWAY_URL="${PUBLIC_GATEWAY_URL:-https://api-miniapp.dmitrybond.tech}"
cd apps/website
pnpm install
pnpm dev -- --host 127.0.0.1 --port 5173

