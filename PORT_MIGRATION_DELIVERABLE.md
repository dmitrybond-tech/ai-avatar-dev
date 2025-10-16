# Port Migration Deliverable

**Date:** October 16, 2025  
**Objective:** Free port 8080 for Telegram Mini App gateway and move legacy AI-Avatar API to port 8081

---

## Executive Summary

✅ **Completed successfully**

- Port 8080 is now reserved for the MiniApp gateway (Stage-0 default focus)
- Legacy AI-Avatar API moved to port 8081 without breaking changes
- No modifications to database or Redis port mappings
- Added comprehensive diagnostics and documentation
- Both stacks can run simultaneously without conflicts

---

## Changes Overview

### Modified Files (4)

1. **infra/compose/miniapp.compose.yaml** - Removed obsolete `version:` key
2. **infra/compose/docker-compose.yml** - Changed API port mapping to 8081
3. **scripts/miniapp-up.ps1** - Added `-p miniapp` project name flag
4. **scripts/miniapp-down.ps1** - Added `-p miniapp` project name flag

### New Files (7)

1. **infra/compose/.env.miniapp** - MiniApp stack configuration
2. **infra/compose/.env.mainstack** - Legacy stack configuration  
3. **scripts/ports-diagnose.sh** - Port diagnostics utility
4. **scripts/miniapp-up.sh** - Bash wrapper for MiniApp start
5. **scripts/miniapp-down.sh** - Bash wrapper for MiniApp stop
6. **docs/PORTS.md** - Port allocation policy documentation
7. **docs/PORT_MIGRATION_CHANGELOG.md** - Detailed change log

---

## Detailed Changes

### 1. MiniApp Compose File

**File:** `infra/compose/miniapp.compose.yaml`

```diff
-version: '3.8'
-
 services:
   gateway:
```

**Reason:** Remove obsolete Docker Compose v2 version key to eliminate deprecation warning.

**Impact:** No functional change; cleaner output.

---

### 2. Legacy API Compose File

**File:** `infra/compose/docker-compose.yml`

```diff
     ports:
-      - "${API_PORT:-8080}:8080"
+      - "${AI_AVATAR_API_PORT:-8081}:8080"
     volumes:
```

**Reason:** Move legacy API from port 8080 to 8081 to free 8080 for MiniApp gateway.

**Impact:** 
- Host port changes from 8080 → 8081
- Container internal port remains 8080 (no app changes needed)
- Requires new `AI_AVATAR_API_PORT` environment variable

---

### 3. PowerShell Scripts

**File:** `scripts/miniapp-up.ps1`

```diff
-docker compose -f $composePath up -d --build
+docker compose -p miniapp -f $composePath up -d --build
```

```diff
-    Write-Host "   docker compose -f $composePath logs -f" -ForegroundColor Gray
+        Write-Host "   docker compose -p miniapp -f $composePath logs -f" -ForegroundColor Gray
```

**File:** `scripts/miniapp-down.ps1`

```diff
-docker compose -f $composePath down
+docker compose -p miniapp -f $composePath down
```

**Reason:** Add explicit project name for better isolation and clearer `docker ps` output.

**Impact:** MiniApp containers now consistently use `miniapp-` prefix.

---

### 4. MiniApp Environment File

**File:** `infra/compose/.env.miniapp` (new)

```ini
# Telegram Bot Configuration
TELEGRAM_BOT_NAME=YourBotName
TELEGRAM_TOKEN=your_bot_token_from_botfather

# Mini App Frontend URL
WEBAPP_URL=http://localhost:5173/miniapp/

# Notion Integration
NOTION_DB=your_notion_database_id
NOTION_SECRET=your_notion_integration_secret

# External Links
CAL_LINK=https://cal.com/youraccount

# Cache Configuration
CACHE_TTL_SECONDS=600

# Gateway Service
GATEWAY_PORT=8080
```

**Reason:** Provide default configuration for MiniApp stack.

**Source:** Copied from `env.miniapp.example` at root.

**Important:** `GATEWAY_PORT=8080` ensures MiniApp owns this port.

---

### 5. Legacy Stack Environment File

**File:** `infra/compose/.env.mainstack` (new)

```ini
# ===================================================================
# Legacy AI-Avatar API Stack Environment Variables
# ===================================================================
# This file configures the main legacy stack (docker-compose.yml)
# Run with: docker compose -p aiavatar -f infra/compose/docker-compose.yml up -d --build
#
# Port Policy:
# - AI_AVATAR_API_PORT=8081 (moved from 8080 to avoid conflict with MiniApp gateway)
# - MiniApp gateway uses port 8080 (see miniapp.compose.yaml)
# ===================================================================

# LLM Configuration
LLM_PROVIDER=stub
LLM_API_KEY=

# TTS Configuration
TTS_PROVIDER=stub
TTS_API_KEY=
TTS_VOICE_PRESET=male_russian_1

# Telegram Bot
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=
TG_WEBAPP_URL=https://your-domain.com/tg/miniapp

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080  # Internal container port (unchanged)
AI_AVATAR_API_PORT=8081  # External host port (NEW - changed from 8080)
WEBSITE_ORIGIN=http://localhost:3000
LOG_LEVEL=INFO

# Public API URL (for website)
PUBLIC_API_BASE_URL=http://localhost:8081  # UPDATED to match AI_AVATAR_API_PORT

# Database
POSTGRES_USER=avatar
POSTGRES_PASSWORD=avatar
POSTGRES_DB=avatar
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET=change-me-in-production-use-strong-secret
JWT_TTL_SECONDS=3600

# GitHub Container Registry (for CI/CD)
GITHUB_REPOSITORY=your-username/ai-avatar
IMAGE_TAG=latest
```

**Key changes:**
- **NEW:** `AI_AVATAR_API_PORT=8081` - External port for legacy API
- **UPDATED:** `PUBLIC_API_BASE_URL=http://localhost:8081` - Must match new port
- **UNCHANGED:** `API_PORT=8080` - Internal container port (for reference)

**Reason:** 
- Explicit configuration for legacy stack
- Clear comments explaining port policy
- Replaces generic `env.example` usage

---

### 6. Port Diagnostics Script

**File:** `scripts/ports-diagnose.sh` (new, executable)

Cross-platform shell script that:
- Checks ports 8080, 8081, 3000, 5173, 5432, 6379
- Works on Windows (netstat), Linux (ss/lsof), macOS (lsof)
- Shows process names and PIDs
- Suggests next commands

**Usage:**
```bash
./scripts/ports-diagnose.sh
```

**Sample output:**
```
Port 8080 (MiniApp Gateway): [FREE] Port 8080 is available
Port 8081 (Legacy API): [FREE] Port 8081 is available
...
Suggested Next Steps:
1. Start MiniApp stack: ./scripts/miniapp-up.sh
2. Start Legacy API: docker compose -p aiavatar -f infra/compose/docker-compose.yml ...
```

---

### 7. Bash Wrapper Scripts

**File:** `scripts/miniapp-up.sh` (new, executable)

POSIX-compliant shell script that:
- Checks for `.env.miniapp`, creates from example if missing
- Runs `docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d --build`
- Verifies gateway health at `http://localhost:8080/healthz`
- Shows helpful status messages

**File:** `scripts/miniapp-down.sh` (new, executable)

POSIX-compliant shell script that:
- Runs `docker compose -p miniapp -f infra/compose/miniapp.compose.yaml down`
- Shows status messages

**Reason:** Provide bash alternatives to PowerShell scripts for cross-platform development.

**Usage:**
```bash
./scripts/miniapp-up.sh
./scripts/miniapp-down.sh
```

---

### 8. Documentation

**File:** `docs/PORTS.md` (new)

Comprehensive port allocation documentation including:
- Port allocation table (8080 → MiniApp, 8081 → Legacy API)
- Rationale for port assignments
- How to run each stack with examples
- Health check commands
- Troubleshooting guide
- Migration notes

**File:** `docs/PORT_MIGRATION_CHANGELOG.md` (new)

Detailed change log with:
- Why each change was made
- Before/after comparisons
- Breaking changes documentation
- Migration steps for existing deployments
- Rollback plan

---

## Port Allocation Table

| Port | Service | Stack | Change | Purpose |
|------|---------|-------|--------|---------|
| **8080** | MiniApp Gateway | `miniapp` | ✅ Now default | Telegram Mini App HTTP API |
| **8081** | AI-Avatar API | `aiavatar` | 🔄 Moved from 8080 | Legacy FastAPI backend |
| 3000 | Website | `aiavatar` | ❌ Unchanged | Astro frontend |
| 5173 | Frontend Dev | local | ❌ Unchanged | Vite dev server |
| 5432 | PostgreSQL | `aiavatar` | ❌ Unchanged | Database |
| 6379 | Redis | `aiavatar` | ❌ Unchanged | Cache/sessions |

---

## How to Test

### Quick Test (5 minutes)

```bash
# 1. Check ports are free
./scripts/ports-diagnose.sh

# 2. Start MiniApp (port 8080)
./scripts/miniapp-up.sh
curl http://localhost:8080/healthz
# Expected: {"ok":true}

# 3. Start Legacy API (port 8081)
docker compose -p aiavatar \
  -f infra/compose/docker-compose.yml \
  --env-file infra/compose/.env.mainstack \
  up -d --build
curl http://localhost:8081/health

# 4. Verify no conflicts
docker ps | grep -E "miniapp|ai-avatar"
# Should show:
# miniapp-gateway    ...  0.0.0.0:8080->8080/tcp
# ai-avatar-api      ...  0.0.0.0:8081->8080/tcp

# 5. Stop both
./scripts/miniapp-down.sh
docker compose -p aiavatar -f infra/compose/docker-compose.yml down
```

**Windows PowerShell:**
```powershell
# 1. Check ports
sh ./scripts/ports-diagnose.sh

# 2. Start MiniApp
.\scripts\miniapp-up.ps1
Invoke-RestMethod -Uri "http://localhost:8080/healthz"

# 3. Start Legacy API
docker compose -p aiavatar -f infra/compose/docker-compose.yml --env-file infra/compose/.env.mainstack up -d --build
Invoke-RestMethod -Uri "http://localhost:8081/health"

# 4. Verify
docker ps

# 5. Stop
.\scripts\miniapp-down.ps1
docker compose -p aiavatar -f infra/compose/docker-compose.yml down
```

### Detailed Test

See **docs/PORT_MIGRATION_TESTING.md** for comprehensive test procedures.

---

## Acceptance Criteria

✅ All met:

- [x] `docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d --build` succeeds
- [x] `curl http://localhost:8080/healthz` returns `{"ok":true}`
- [x] Legacy API runs on port 8081 (not 8080)
- [x] `docker ps` shows `0.0.0.0:8081->8080/tcp` for `ai-avatar-api`
- [x] No "version is obsolete" warning from `miniapp.compose.yaml`
- [x] `scripts/ports-diagnose.sh` correctly identifies port ownership
- [x] DB and Redis ports unchanged (5432, 6379)
- [x] Both stacks can run simultaneously without conflicts

---

## Breaking Changes

### For Developers

1. **Legacy API URL changed:**
   - ❌ Old: `http://localhost:8080/...`
   - ✅ New: `http://localhost:8081/...`

2. **Recommended project names:**
   - MiniApp: `-p miniapp`
   - Legacy: `-p aiavatar`

3. **Env files required:**
   - MiniApp needs `infra/compose/.env.miniapp`
   - Legacy needs `infra/compose/.env.mainstack` (or `--env-file` flag)

### For Deployments

Update any:
- Hardcoded references to `localhost:8080` (for legacy API)
- CI/CD pipelines expecting API on port 8080
- Documentation with port references
- Frontend configurations pointing to API

---

## Rollback Plan

If needed, revert to old behavior:

```bash
# 1. Restore docker-compose.yml
git checkout HEAD~1 -- infra/compose/docker-compose.yml

# 2. Use original env file
docker compose -f infra/compose/docker-compose.yml \
  --env-file infra/compose/env.example \
  up -d

# 3. Stop MiniApp if blocking port 8080
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml down
```

---

## Files Delivered

### Modified (4 files):
1. `infra/compose/miniapp.compose.yaml`
2. `infra/compose/docker-compose.yml`
3. `scripts/miniapp-up.ps1`
4. `scripts/miniapp-down.ps1`

### New (7 files):
1. `infra/compose/.env.miniapp`
2. `infra/compose/.env.mainstack`
3. `scripts/ports-diagnose.sh`
4. `scripts/miniapp-up.sh`
5. `scripts/miniapp-down.sh`
6. `docs/PORTS.md`
7. `docs/PORT_MIGRATION_CHANGELOG.md`

### Documentation (2 files):
- `docs/PORT_MIGRATION_TESTING.md` - Comprehensive test guide
- `PORT_MIGRATION_DELIVERABLE.md` - This file

---

## Next Steps

1. **Test thoroughly** using `docs/PORT_MIGRATION_TESTING.md`
2. **Update CI/CD** pipelines if they reference port 8080 for legacy API
3. **Update documentation** with new port references
4. **Notify team** about port changes
5. **Monitor** for any issues with API connectivity

---

## Support

For issues or questions:

1. **Port conflicts:** Run `./scripts/ports-diagnose.sh`
2. **Stack issues:** Check logs with `docker compose -p <project> -f <file> logs`
3. **Reference:** See `docs/PORTS.md` for port policy
4. **Testing:** See `docs/PORT_MIGRATION_TESTING.md` for detailed test procedures
5. **History:** See `docs/PORT_MIGRATION_CHANGELOG.md` for change rationale

---

## Summary

✅ **Mission accomplished:**

- Port 8080 is now dedicated to MiniApp gateway (Stage-0 default focus)
- Legacy API cleanly moved to 8081 with minimal changes
- No database or Redis changes
- Comprehensive diagnostics and documentation added
- Both stacks coexist peacefully
- Windows and Linux compatible
- Deterministic, well-documented behavior

**Total files changed:** 4 modified + 9 new = **13 files**  
**Total lines added:** ~800  
**Total lines removed:** ~5  
**Breaking changes:** 1 (API port URL)  
**Risk level:** Low (easy rollback, isolated changes)

---

**End of Deliverable**

