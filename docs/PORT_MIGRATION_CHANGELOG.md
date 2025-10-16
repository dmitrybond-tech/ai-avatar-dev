# Port Migration Change Log

**Date:** October 16, 2025  
**Goal:** Free port 8080 for MiniApp gateway, move legacy AI-Avatar API to 8081

## Changes Made

### 1. MiniApp Stack Updates

#### File: `infra/compose/miniapp.compose.yaml`
**Change:** Removed obsolete `version: '3.8'` key
- **Why:** Docker Compose v2 no longer requires version key; removes deprecation warning
- **Impact:** No functional change; cleaner compose file

#### File: `infra/compose/.env.miniapp`
**Status:** Created from `env.miniapp.example`
- **Why:** Provides default configuration for MiniApp stack
- **Key setting:** `GATEWAY_PORT=8080` (default focus for Stage-0)
- **Impact:** MiniApp gateway now consistently uses port 8080

### 2. Legacy AI-Avatar API Stack Updates

#### File: `infra/compose/docker-compose.yml`
**Change:** Updated API service port mapping
```yaml
# Before
ports:
  - "${API_PORT:-8080}:8080"

# After  
ports:
  - "${AI_AVATAR_API_PORT:-8081}:8080"
```
- **Why:** Move legacy API to port 8081 to free 8080 for MiniApp
- **Impact:** Legacy API now binds to host port 8081; internal container port unchanged
- **Container port:** Still 8080 (no application changes needed)

#### File: `infra/compose/.env.mainstack`
**Status:** Created
- **Why:** Dedicated env file for legacy stack with explicit port configuration
- **Key settings:**
  - `AI_AVATAR_API_PORT=8081` (new host port)
  - `API_PORT=8080` (internal, for reference)
  - `PUBLIC_API_BASE_URL=http://localhost:8081` (updated to match)
- **Impact:** Clear separation of MiniApp and legacy configurations
- **Usage:** `docker compose --env-file infra/compose/.env.mainstack ...`

### 3. Developer Tools

#### File: `scripts/ports-diagnose.sh`
**Status:** Created (executable)
- **Why:** Help developers quickly diagnose port conflicts
- **Features:**
  - Cross-platform (Windows/Linux)
  - Checks ports 8080, 8081, 3000, 5173, 5432, 6379
  - Shows process names and PIDs
  - Suggests next steps
- **Usage:** `./scripts/ports-diagnose.sh`

#### Files: `scripts/miniapp-up.sh` and `scripts/miniapp-down.sh`
**Status:** Created (executable)
- **Why:** Bash alternatives to PowerShell scripts for cross-platform dev
- **Features:**
  - POSIX sh compatible (works in Git Bash, WSL, Linux, macOS)
  - Uses `-p miniapp` for consistent project naming
  - Auto-creates `.env.miniapp` from example if missing
  - Health check verification
- **Usage:**
  ```bash
  ./scripts/miniapp-up.sh
  ./scripts/miniapp-down.sh
  ```

#### Files: `scripts/miniapp-up.ps1` and `scripts/miniapp-down.ps1`
**Changes:** Updated to use `-p miniapp` flag
- **Why:** Consistent project naming across platforms
- **Before:** `docker compose -f ...`
- **After:** `docker compose -p miniapp -f ...`
- **Impact:** Better isolation; clearer `docker ps` output

### 4. Documentation

#### File: `docs/PORTS.md`
**Status:** Created
- **Why:** Central reference for port allocation strategy
- **Contents:**
  - Port allocation table
  - Rationale for port assignments
  - How to run each stack
  - Health check examples
  - Troubleshooting guide
  - Migration notes
- **Impact:** Single source of truth for port policy

## Port Allocation Summary

| Port | Service | Stack | Change |
|------|---------|-------|--------|
| 8080 | MiniApp Gateway | `miniapp` | **Now default focus** |
| 8081 | Legacy AI-Avatar API | `aiavatar` | **Moved from 8080** |
| 3000 | Website | `aiavatar` | Unchanged |
| 5173 | Frontend Dev | local | Unchanged |
| 5432 | PostgreSQL | `aiavatar` | Unchanged |
| 6379 | Redis | `aiavatar` | Unchanged |

## Breaking Changes

### For Developers

1. **Legacy API URL changed:**
   - Old: `http://localhost:8080/...`
   - New: `http://localhost:8081/...`

2. **Must use env files:**
   - MiniApp: Requires `infra/compose/.env.miniapp`
   - Legacy: Recommended `infra/compose/.env.mainstack`

3. **Compose project names:**
   - MiniApp scripts now use `-p miniapp`
   - Legacy stack recommended: `-p aiavatar`

### Migration Steps for Existing Deployments

1. Stop legacy API: `docker compose -f infra/compose/docker-compose.yml down`
2. Update env: Copy `infra/compose/.env.mainstack` and configure
3. Restart with new port: `docker compose -p aiavatar -f infra/compose/docker-compose.yml --env-file infra/compose/.env.mainstack up -d`
4. Update any hardcoded references from `:8080` to `:8081`

## Testing Checklist

- [ ] Port 8080 is free before starting
- [ ] MiniApp starts successfully on 8080
- [ ] Legacy API starts successfully on 8081
- [ ] No "version is obsolete" warning
- [ ] Health checks pass for both stacks
- [ ] `docker ps` shows correct port mappings
- [ ] Both stacks can run simultaneously

## Files Changed

### Modified:
1. `infra/compose/miniapp.compose.yaml` - Removed `version:` key
2. `infra/compose/docker-compose.yml` - Changed port mapping to `AI_AVATAR_API_PORT`
3. `scripts/miniapp-up.ps1` - Added `-p miniapp` flag
4. `scripts/miniapp-down.ps1` - Added `-p miniapp` flag

### Created:
1. `infra/compose/.env.miniapp` - MiniApp configuration
2. `infra/compose/.env.mainstack` - Legacy API configuration
3. `scripts/ports-diagnose.sh` - Port diagnostics tool
4. `scripts/miniapp-up.sh` - Bash wrapper for MiniApp start
5. `scripts/miniapp-down.sh` - Bash wrapper for MiniApp stop
6. `docs/PORTS.md` - Port allocation documentation
7. `docs/PORT_MIGRATION_CHANGELOG.md` - This file

## Rollback Plan

If issues arise, restore legacy behavior:

1. In `docker-compose.yml`, change back to:
   ```yaml
   ports:
     - "${API_PORT:-8080}:8080"
   ```

2. Use original env file:
   ```bash
   docker compose -f infra/compose/docker-compose.yml --env-file infra/compose/env.example up -d
   ```

3. Stop MiniApp if it's blocking port 8080

## Next Steps

- Update CI/CD pipelines if they reference port 8080 for legacy API
- Update any documentation with hardcoded port references
- Consider updating website build args if it depends on API port
- Test both stacks in production-like environment

## References

- [PORTS.md](PORTS.md) - Port allocation policy
- [MINIAPP_QUICKSTART.md](../MINIAPP_QUICKSTART.md) - MiniApp setup
- Docker Compose project naming: `-p` flag documentation

