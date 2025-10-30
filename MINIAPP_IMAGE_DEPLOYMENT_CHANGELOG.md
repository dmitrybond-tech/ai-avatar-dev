# MiniApp Image-based Deployment Changelog

## Overview
Switched the mini-app stack to image-based deployment from GHCR (GitHub Container Registry), fixed the Telegram bot for aiogram 3.7+, and ensured stable runtime ports for API and Web behind Caddy.

## Changes Made

### 1. Bot (aiogram 3.7+ fix)
**File**: `apps/miniapp-bot/main.py`
- ✅ **Fixed**: Bot was already using correct `DefaultBotProperties` pattern for aiogram 3.7+
- ✅ **Added**: Missing `dp = Dispatcher()` declaration
- ✅ **Verified**: Early fail for empty `TELEGRAM_TOKEN` already present
- ✅ **Verified**: `BOT_MODE=polling` is supported (default) and webhook is OFF by default

### 2. Image-first Compose Configuration
**File**: `infra/compose/miniapp.compose.yaml`
- ✅ **Replaced**: All `build:` sections with `image:` references
- ✅ **Added**: `pull_policy: always` for all services
- ✅ **Updated**: Image references to use environment variables:
  - `image: ${IMAGE_API}:${IMAGE_TAG}`
  - `image: ${IMAGE_WEB}:${IMAGE_TAG}`
  - `image: ${IMAGE_BOT}:${IMAGE_TAG}`
- ✅ **Removed**: Host port mappings (moved to runtime override)
- ✅ **Kept**: All environment variables and health checks intact

### 3. Runtime Port Configuration
**File**: `infra/compose/miniapp.runtime.yml`
- ✅ **Verified**: Correct port mappings already present:
  - API: `127.0.0.1:8081:8080`
  - Web: `127.0.0.1:5175:80`

### 4. Environment Configuration
**File**: `infra/compose/env.miniapp.example`
- ✅ **Added**: GHCR image configuration section
- ✅ **Updated**: Image references to GHCR:
  - `IMAGE_API=ghcr.io/dmitrybond-tech/ai-avatar-miniapp-api`
  - `IMAGE_WEB=ghcr.io/dmitrybond-tech/ai-avatar-miniapp-web`
  - `IMAGE_BOT=ghcr.io/dmitrybond-tech/ai-avatar-miniapp-bot`
- ✅ **Updated**: `TELEGRAM_BOT_NAME=db_ai_avatar_bot`
- ✅ **Updated**: `TELEGRAM_TOKEN=__REQUIRED_FROM_BOTFATHER__`
- ✅ **Updated**: `WEBAPP_URL=https://miniapp.dmitrybond.tech`
- ✅ **Added**: Comprehensive documentation and comments

### 5. Local Build Override
**File**: `infra/compose/miniapp.build.yml` (NEW)
- ✅ **Created**: Optional build override for local development
- ✅ **Added**: Build contexts and Dockerfiles for all services
- ✅ **Added**: Build args for web service (Vite configuration)
- ✅ **Usage**: `docker compose -f miniapp.compose.yaml -f miniapp.build.yml -f miniapp.runtime.yml up -d --build`

### 6. CI/CD Workflow
**File**: `.github/workflows/ci-images.yml` (NEW)
- ✅ **Created**: GitHub Actions workflow for building and pushing images to GHCR
- ✅ **Triggers**: Push to `main` and `feature/miniapp-containers` branches, tags, manual dispatch
- ✅ **Services**: Builds and pushes three images:
  - `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-api`
  - `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-web`
  - `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-bot`
- ✅ **Tags**: `main`, `feature-miniapp-containers`, `sha-<shortsha>`, `latest` (for tags), semver tags
- ✅ **Tools**: Uses deterministic versions:
  - `actions/checkout@v4`
  - `docker/setup-qemu-action@v3`
  - `docker/setup-buildx-action@v3`
  - `docker/build-push-action@v6`
  - `docker/metadata-action@v5`
- ✅ **Build Args**: Includes Vite configuration for web service

### 7. Documentation Updates
**File**: `README.md`
- ✅ **Updated**: MiniApp deployment section with image-based approach
- ✅ **Added**: GHCR authentication instructions
- ✅ **Added**: Image-based deployment commands
- ✅ **Added**: Local development build instructions
- ✅ **Updated**: Smoke tests with correct ports (8081 for API, 5175 for Web)
- ✅ **Added**: Production deployment with GHCR images

## Deployment Instructions

### Production (Image-based)
```bash
# 1. Authenticate to GHCR
docker login ghcr.io -u <github-username> -p <PAT>

# 2. Setup environment
cd infra/compose
cp env.miniapp.example .env.miniapp
# Edit .env.miniapp and set TELEGRAM_TOKEN

# 3. Deploy
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml \
  --env-file .env.miniapp pull

docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml \
  --env-file .env.miniapp up -d
```

### Local Development (Build from Source)
```bash
# Use build override for local development
docker compose -f miniapp.compose.yaml -f miniapp.build.yml \
  -f miniapp.runtime.yml --env-file .env.miniapp up -d --build
```

## Verification

### Smoke Tests
```bash
# Test API health
curl -s --http2 https://miniapp.dmitrybond.tech/healthz
# Expected: {"status":"ok"}

# Test API rules
curl -s --http2 'https://miniapp.dmitrybond.tech/rules?lang=ru'
# Expected: JSON with labels and scenes

# Test web app
curl -sI --http2 https://miniapp.dmitrybond.tech/miniapp/
# Expected: 200 OK with HTML content

# Check bot logs
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml \
  --env-file .env.miniapp logs -f bot
# Expected: Bot shows "online" status, no parse_mode errors
```

## Runtime Ports
- **API**: `127.0.0.1:8081` → container `api:8080`
- **Web**: `127.0.0.1:5175` → container `web:80`
- **Bot**: No exposed ports (polling mode)

## Image References
- **API**: `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-api:main`
- **Web**: `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-web:main`
- **Bot**: `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-bot:main`

## Benefits
1. **Faster Deployments**: No build time on production servers
2. **Consistent Images**: Same images across all environments
3. **Better Caching**: Docker layer caching in GHCR
4. **Easier Rollbacks**: Tag-based deployments
5. **Reduced Server Load**: No compilation on production
6. **Better Security**: Pre-built images with known dependencies

## Backward Compatibility
- Local development still supported via `miniapp.build.yml`
- All existing environment variables preserved
- Service names and network configuration unchanged
- Runtime ports remain the same (8081 for API, 5175 for Web)
