# Port Policy and Configuration

This document describes the port allocation strategy for the AI-Avatar monorepo, which contains multiple independent compose stacks.

## Port Allocation

| Port | Service | Stack | Description |
|------|---------|-------|-------------|
| **8080** | MiniApp Gateway | `miniapp` | Telegram Mini App HTTP gateway (default focus) |
| **8081** | Legacy AI-Avatar API | `aiavatar` | Original FastAPI backend (moved from 8080) |
| 3000 | Website | `aiavatar` | Astro-based frontend |
| 5173 | Frontend Dev | local | Vite dev server (when running locally) |
| 5432 | PostgreSQL | `aiavatar` | Database (default, configurable) |
| 6379 | Redis | `aiavatar` | Cache/session store |

## Rationale

**Why port 8080 for MiniApp?**
- Stage-0 goal: Make MiniApp (gateway + bot) the primary focus
- MiniApp gateway is simpler and more actively developed
- Legacy API moved to 8081 to avoid conflicts

**Why separate compose stacks?**
- Different deployment lifecycles
- Independent scaling and configuration
- Clearer separation of concerns

## Running the Stacks

### MiniApp Stack (gateway + bot)

**Compose file:** `infra/compose/miniapp.compose.yaml`  
**Env file:** `infra/compose/.env.miniapp` (copy from `env.miniapp.example`)  
**Project name:** `miniapp`

```bash
# Quick start (PowerShell)
.\scripts\miniapp-up.ps1

# Quick start (bash)
./scripts/miniapp-up.sh

# Manual
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d --build

# Stop
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml down
```

**Health check:**
```bash
curl http://localhost:8080/healthz
# Expected: {"ok":true}
```

### Legacy AI-Avatar API Stack (api + db + redis + website + telegram)

**Compose file:** `infra/compose/docker-compose.yml`  
**Env file:** `infra/compose/.env.mainstack` (copy from `infra/compose/env.example`)  
**Project name:** `aiavatar`

```bash
# Start
docker compose -p aiavatar \
  -f infra/compose/docker-compose.yml \
  --env-file infra/compose/.env.mainstack \
  up -d --build

# Stop
docker compose -p aiavatar \
  -f infra/compose/docker-compose.yml \
  down
```

**Health check:**
```bash
curl http://localhost:8081/health
# (or check the API's health endpoint)
```

**Website:**
```
http://localhost:3000
```

## Port Diagnostics

Run the diagnostics script to check which ports are occupied:

```bash
# Unix/Git Bash
./scripts/ports-diagnose.sh

# PowerShell (if sh available via Git Bash)
sh ./scripts/ports-diagnose.sh
```

This will show:
- Which ports are free or occupied
- Process IDs and names (where available)
- Suggested commands to start each stack

## Environment Variables

### MiniApp Stack

Key variables in `infra/compose/.env.miniapp`:
- `GATEWAY_PORT=8080` - External port for gateway
- `TELEGRAM_TOKEN` - Bot token from @BotFather
- `WEBAPP_URL` - Frontend URL for the mini app
- `NOTION_DB`, `NOTION_SECRET` - Notion integration

### Legacy AI-Avatar Stack

Key variables in `infra/compose/.env.mainstack`:
- `AI_AVATAR_API_PORT=8081` - **External port for legacy API (changed from 8080)**
- `API_PORT=8080` - Internal container port (unchanged)
- `PUBLIC_API_BASE_URL=http://localhost:8081` - Must match `AI_AVATAR_API_PORT`
- `POSTGRES_PORT=5432` - Database port
- Various API keys (LLM, TTS, Telegram)

## Troubleshooting

### Port 8080 is already in use

1. Check what's using it:
   ```bash
   ./scripts/ports-diagnose.sh
   ```

2. If it's the legacy API, stop it:
   ```bash
   docker compose -p aiavatar -f infra/compose/docker-compose.yml down
   ```

3. If it's another process:
   - **Windows:** `netstat -ano | findstr :8080` then `taskkill /PID <pid> /F`
   - **Linux:** `lsof -i :8080` or `fuser -k 8080/tcp`

### Both stacks running at once

This is supported! They use different ports:
- MiniApp gateway: `:8080`
- Legacy API: `:8081`
- Website: `:3000`

Both can share the same DB/Redis if configured, or run independently.

### Port conflicts with other projects

Edit the respective `.env` file:
- **MiniApp:** Change `GATEWAY_PORT` in `infra/compose/.env.miniapp`
- **Legacy API:** Change `AI_AVATAR_API_PORT` in `infra/compose/.env.mainstack`

Remember to update `PUBLIC_API_BASE_URL` if you change `AI_AVATAR_API_PORT`.

## Migration Notes

**October 2025 Update:**
- Legacy AI-Avatar API moved from port 8080 → 8081
- MiniApp gateway now owns port 8080 (Stage-0 default)
- Introduced `AI_AVATAR_API_PORT` env var for legacy API
- Removed obsolete `version:` key from `miniapp.compose.yaml`
- All port mappings now use environment variables with sane defaults

**Old behavior:**
```yaml
# docker-compose.yml (old)
ports:
  - "${API_PORT:-8080}:8080"  # Used to map to host 8080
```

**New behavior:**
```yaml
# docker-compose.yml (new)
ports:
  - "${AI_AVATAR_API_PORT:-8081}:8080"  # Maps to host 8081
```

Internal container port remains `8080` for both services - only the host binding changed.

## See Also

- [MINIAPP_QUICKSTART.md](../MINIAPP_QUICKSTART.md) - MiniApp setup guide
- [VM_BUILD_FIXES_QUICKSTART.md](../VM_BUILD_FIXES_QUICKSTART.md) - Docker DNS and build fixes
- [README.md](../README.md) - Project overview

