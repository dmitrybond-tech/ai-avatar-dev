#!/bin/sh
# Start Mini App services (gateway + bot)
# Cross-platform wrapper for docker compose

set -e

ENV_PATH="infra/compose/.env.miniapp"
EXAMPLE_PATH="env.miniapp.example"
COMPOSE_PATH="infra/compose/miniapp.compose.yaml"

echo "🚀 Starting Mini App services..."

# Check if .env.miniapp exists, if not copy from example
if [ ! -f "$ENV_PATH" ]; then
    echo "📋 .env.miniapp not found. Copying from example..."
    
    if [ -f "$EXAMPLE_PATH" ]; then
        cp "$EXAMPLE_PATH" "$ENV_PATH"
        echo "✅ Created $ENV_PATH"
        echo ""
        echo "⚠️  IMPORTANT: Please edit $ENV_PATH and set your configuration:"
        echo "   - TELEGRAM_TOKEN (from @BotFather)"
        echo "   - NOTION_DB (your Notion database ID)"
        echo "   - NOTION_SECRET (your Notion integration secret)"
        echo "   - WEBAPP_URL (URL where frontend will run)"
        echo "   - CAL_LINK (your booking calendar link)"
        echo ""
        echo "After configuration, run this script again."
        exit 0
    else
        echo "❌ Error: $EXAMPLE_PATH not found!"
        exit 1
    fi
fi

# Start services with Docker Compose
echo "🐳 Building and starting containers..."
docker compose -p miniapp -f "$COMPOSE_PATH" up -d --build

if [ $? -ne 0 ]; then
    echo "❌ Failed to start services"
    exit 1
fi

# Wait a moment for services to initialize
sleep 3

# Check gateway health
echo ""
echo "🔍 Checking gateway health..."

if command -v curl >/dev/null 2>&1; then
    if curl -sf http://localhost:8080/healthz >/dev/null; then
        echo "✅ Gateway is healthy!"
        echo ""
        echo "🎉 Mini App services are running!"
        echo ""
        echo "📡 Gateway API: http://localhost:8080"
        echo "   - GET  /healthz"
        echo "   - POST /reply {text}"
        echo "   - POST /refresh"
        echo ""
        echo "🤖 Telegram bot is polling..."
        echo ""
        echo "To stop: ./scripts/miniapp-down.sh"
    else
        echo "⚠️  Could not reach gateway health endpoint"
        echo "   Services may still be starting up. Check logs with:"
        echo "   docker compose -p miniapp -f $COMPOSE_PATH logs -f"
    fi
else
    echo "⚠️  curl not found, skipping health check"
    echo "   Verify manually: docker compose -p miniapp -f $COMPOSE_PATH ps"
fi

echo ""

