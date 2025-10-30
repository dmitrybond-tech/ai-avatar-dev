# MiniApp Image-based Deployment - Implementation Summary

## Files Modified

### 1. `apps/miniapp-bot/main.py`
**Changes**: Added missing `dp = Dispatcher()` declaration
- **Line 25**: Added `dp = Dispatcher()` after imports
- **Rationale**: Bot was already using correct aiogram 3.7+ pattern with `DefaultBotProperties`

### 2. `infra/compose/miniapp.compose.yaml`
**Changes**: Converted from build-based to image-based deployment
- **Lines 3-17**: Replaced `build:` section with `image: ${IMAGE_API}:${IMAGE_TAG}` and `pull_policy: always`
- **Lines 19-32**: Replaced `build:` section with `image: ${IMAGE_BOT}:${IMAGE_TAG}` and `pull_policy: always`
- **Lines 34-43**: Replaced `build:` section with `image: ${IMAGE_WEB}:${IMAGE_TAG}` and `pull_policy: always`
- **Removed**: All `build:` contexts, dockerfiles, and build args
- **Removed**: Host port mappings (moved to runtime override)

### 3. `infra/compose/miniapp.runtime.yml`
**Changes**: No changes needed - already had correct ports
- **Verified**: API port `127.0.0.1:8081:8080` ✓
- **Verified**: Web port `127.0.0.1:5175:80` ✓

### 4. `infra/compose/env.miniapp.example`
**Changes**: Updated with GHCR image references and better documentation
- **Lines 5-11**: Added GHCR image configuration section
- **Line 7**: `IMAGE_TAG=main`
- **Lines 9-11**: Added image references for API, Web, and Bot
- **Line 15**: `TELEGRAM_TOKEN=__REQUIRED_FROM_BOTFATHER__`
- **Line 16**: `TELEGRAM_BOT_NAME=db_ai_avatar_bot`
- **Line 33**: `WEBAPP_URL=https://miniapp.dmitrybond.tech`
- **Added**: Comprehensive comments and documentation

### 5. `infra/compose/miniapp.build.yml` (NEW)
**Changes**: Created optional build override for local development
- **Lines 1-30**: Complete file with build contexts and dockerfiles
- **Usage**: `docker compose -f miniapp.compose.yaml -f miniapp.build.yml -f miniapp.runtime.yml up -d --build`

### 6. `.github/workflows/ci-images.yml` (NEW)
**Changes**: Created CI workflow for building and pushing to GHCR
- **Lines 1-100**: Complete workflow file
- **Triggers**: Push to main/feature branches, tags, manual dispatch
- **Services**: API, Web, Bot with deterministic tool versions
- **Tags**: main, feature-miniapp-containers, sha-*, latest, semver

### 7. `README.md`
**Changes**: Updated MiniApp section with image-based deployment
- **Lines 357-447**: Replaced entire MiniApp deployment section
- **Added**: GHCR authentication instructions
- **Added**: Image-based deployment commands
- **Added**: Local development build instructions
- **Updated**: Smoke tests with correct ports

## Key Benefits

1. **Production Ready**: Images built once, deployed everywhere
2. **Faster Deployments**: No build time on production servers
3. **Consistent Environments**: Same images across dev/staging/prod
4. **Better Caching**: Docker layer caching in GHCR
5. **Easier Rollbacks**: Tag-based deployments
6. **Reduced Server Load**: No compilation on production

## Deployment Commands

### Production (Image-based)
```bash
# Authenticate
docker login ghcr.io -u <username> -p <PAT>

# Deploy
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml \
  --env-file .env.miniapp pull

docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml \
  --env-file .env.miniapp up -d
```

### Local Development (Build from Source)
```bash
docker compose -f miniapp.compose.yaml -f miniapp.build.yml \
  -f miniapp.runtime.yml --env-file .env.miniapp up -d --build
```

## Verification

### Smoke Tests
```bash
# API health
curl -s --http2 https://miniapp.dmitrybond.tech/healthz
# Expected: {"status":"ok"}

# API rules
curl -s --http2 'https://miniapp.dmitrybond.tech/rules?lang=ru'
# Expected: JSON with labels and scenes

# Web app
curl -sI --http2 https://miniapp.dmitrybond.tech/miniapp/
# Expected: 200 OK

# Bot logs
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml \
  --env-file .env.miniapp logs -f bot
# Expected: "online" status, no parse_mode errors
```

## Runtime Configuration

- **API**: `127.0.0.1:8081` → container `api:8080`
- **Web**: `127.0.0.1:5175` → container `web:80`
- **Bot**: No exposed ports (polling mode)

## Image References

- **API**: `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-api:main`
- **Web**: `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-web:main`
- **Bot**: `ghcr.io/dmitrybond-tech/ai-avatar-miniapp-bot:main`

## Backward Compatibility

- ✅ Local development still supported via `miniapp.build.yml`
- ✅ All existing environment variables preserved
- ✅ Service names and network configuration unchanged
- ✅ Runtime ports remain the same
- ✅ No breaking changes to existing workflows
