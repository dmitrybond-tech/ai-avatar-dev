#!/bin/sh
# Stop Mini App services
# Cross-platform wrapper for docker compose

set -e

COMPOSE_PATH="infra/compose/miniapp.compose.yaml"

echo "🛑 Stopping Mini App services..."

docker compose -p miniapp -f "$COMPOSE_PATH" down

if [ $? -eq 0 ]; then
    echo "✅ Services stopped successfully"
else
    echo "❌ Failed to stop services"
    exit 1
fi

echo ""

