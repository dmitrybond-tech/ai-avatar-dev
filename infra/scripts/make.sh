#!/usr/bin/env bash
# Bash helper script for common tasks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$SCRIPT_DIR/../compose"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"

cd "$COMPOSE_DIR"

case "$1" in
  up)
    echo "Starting all services..."
    docker compose -f docker-compose.yml up -d
    ;;
  down)
    echo "Stopping all services..."
    docker compose -f docker-compose.yml down
    ;;
  build)
    echo "Building all images..."
    docker compose -f docker-compose.yml build
    ;;
  logs)
    echo "Showing logs (Ctrl+C to exit)..."
    docker compose -f docker-compose.yml logs -f
    ;;
  restart)
    echo "Restarting all services..."
    docker compose -f docker-compose.yml restart
    ;;
  clean)
    echo "Cleaning up (removes volumes)..."
    read -p "This will delete all data. Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      docker compose -f docker-compose.yml down -v
      echo "Cleanup complete."
    else
      echo "Cancelled."
    fi
    ;;
  *)
    echo "Usage: $0 {up|down|build|logs|restart|clean}"
    exit 1
    ;;
esac

