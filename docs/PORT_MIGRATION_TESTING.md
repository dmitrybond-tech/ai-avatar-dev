# Port Migration Testing Guide

This guide walks through testing the port migration changes to ensure everything works correctly.

## Prerequisites

- Docker and Docker Compose installed
- Git repository up to date with port migration changes
- No services currently running on ports 8080 or 8081

## Test Sequence

### Step 1: Check Current Port Status

```bash
# Run diagnostics
./scripts/ports-diagnose.sh

# Expected output:
# [FREE] Port 8080 is available
# [FREE] Port 8081 is available
```

**On Windows PowerShell:**
```powershell
sh ./scripts/ports-diagnose.sh
# OR manually:
netstat -ano | findstr ":8080"
netstat -ano | findstr ":8081"
```

**Verification:**
- [ ] Port 8080 shows as free
- [ ] Port 8081 shows as free

---

### Step 2: Test MiniApp Stack (Port 8080)

#### 2.1 Start MiniApp

**Using wrapper script (recommended):**
```bash
# Bash/Git Bash
./scripts/miniapp-up.sh

# PowerShell
.\scripts\miniapp-up.ps1
```

**Manual command:**
```bash
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d --build
```

**Expected output:**
- ✅ No "version is obsolete" warning
- ✅ Containers build successfully
- ✅ Services start without errors

#### 2.2 Verify MiniApp Health

```bash
curl http://localhost:8080/healthz
```

**Expected response:**
```json
{"ok":true}
```

**On Windows PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/healthz"
```

**Verification:**
- [ ] Gateway responds on port 8080
- [ ] Health check returns `{"ok":true}`
- [ ] No errors in logs: `docker compose -p miniapp -f infra/compose/miniapp.compose.yaml logs`

#### 2.3 Check Container Status

```bash
docker ps | grep miniapp
```

**Expected output:**
```
miniapp-gateway   ...   0.0.0.0:8080->8080/tcp   ...
miniapp-bot       ...                            ...
```

**Verification:**
- [ ] `miniapp-gateway` shows `0.0.0.0:8080->8080/tcp`
- [ ] `miniapp-bot` is running
- [ ] Both containers are healthy

#### 2.4 Stop MiniApp (optional for now)

```bash
./scripts/miniapp-down.sh
# OR PowerShell: .\scripts\miniapp-down.ps1
# OR Manual: docker compose -p miniapp -f infra/compose/miniapp.compose.yaml down
```

---

### Step 3: Test Legacy AI-Avatar API Stack (Port 8081)

#### 3.1 Ensure .env.mainstack Exists

```bash
# Check if file exists
ls infra/compose/.env.mainstack

# If missing, create from template (should already be done)
cp infra/compose/env.example infra/compose/.env.mainstack
```

**Edit `infra/compose/.env.mainstack` and set:**
- Required secrets (TELEGRAM_BOT_TOKEN, API keys, etc.)
- Verify `AI_AVATAR_API_PORT=8081`
- Verify `PUBLIC_API_BASE_URL=http://localhost:8081`

#### 3.2 Start Legacy Stack

```bash
docker compose -p aiavatar \
  -f infra/compose/docker-compose.yml \
  --env-file infra/compose/.env.mainstack \
  up -d --build
```

**Expected output:**
- ✅ Builds complete successfully
- ✅ DB and Redis start first (health checks pass)
- ✅ API starts after dependencies are healthy
- ✅ Website and Telegram bot start

#### 3.3 Verify Legacy API Health

```bash
# Check which health endpoint the API uses
curl http://localhost:8081/health
# OR
curl http://localhost:8081/docs  # Should show OpenAPI docs
```

**On Windows PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8081/health"
```

**Verification:**
- [ ] API responds on port 8081 (NOT 8080)
- [ ] Health endpoint returns success
- [ ] API docs accessible at `http://localhost:8081/docs`

#### 3.4 Check Container Status

```bash
docker ps | grep ai-avatar
```

**Expected output:**
```
ai-avatar-api       ...   0.0.0.0:8081->8080/tcp   ...
ai-avatar-db        ...   0.0.0.0:5432->5432/tcp   ...
ai-avatar-redis     ...   0.0.0.0:6379->6379/tcp   ...
ai-avatar-website   ...   0.0.0.0:3000->3000/tcp   ...
ai-avatar-telegram  ...                            ...
```

**Verification:**
- [ ] `ai-avatar-api` shows `0.0.0.0:8081->8080/tcp` (NOT 8080->8080)
- [ ] DB on port 5432 (unchanged)
- [ ] Redis on port 6379 (unchanged)
- [ ] Website on port 3000 (unchanged)
- [ ] All containers are healthy

#### 3.5 Test Website

```bash
# Visit in browser
http://localhost:3000
```

**Verification:**
- [ ] Website loads successfully
- [ ] Website can communicate with API on port 8081
- [ ] No console errors related to API connection

---

### Step 4: Test Both Stacks Running Simultaneously

This is the critical test - both stacks should coexist without port conflicts.

#### 4.1 Start MiniApp (if stopped)

```bash
./scripts/miniapp-up.sh
```

#### 4.2 Verify Both Endpoints

```bash
# MiniApp Gateway
curl http://localhost:8080/healthz

# Legacy API
curl http://localhost:8081/health
```

**Verification:**
- [ ] Port 8080 responds (MiniApp)
- [ ] Port 8081 responds (Legacy API)
- [ ] No port conflicts in logs
- [ ] Both stacks function independently

#### 4.3 Check All Containers

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "miniapp|ai-avatar"
```

**Expected output:**
```
miniapp-gateway     0.0.0.0:8080->8080/tcp
miniapp-bot         
ai-avatar-api       0.0.0.0:8081->8080/tcp
ai-avatar-db        0.0.0.0:5432->5432/tcp
ai-avatar-redis     0.0.0.0:6379->6379/tcp
ai-avatar-website   0.0.0.0:3000->3000/tcp
ai-avatar-telegram  
```

**Verification:**
- [ ] 8080 belongs to `miniapp-gateway`
- [ ] 8081 belongs to `ai-avatar-api`
- [ ] No overlapping port assignments

---

### Step 5: Test Diagnostics Script

```bash
./scripts/ports-diagnose.sh
```

**Expected output:**
```
Port 8080 (MiniApp Gateway): [OCCUPIED] by miniapp-gateway
Port 8081 (Legacy API): [OCCUPIED] by ai-avatar-api
Port 3000 (Website): [OCCUPIED] by ai-avatar-website
Port 5432 (PostgreSQL): [OCCUPIED] by ai-avatar-db
Port 6379 (Redis): [OCCUPIED] by ai-avatar-redis
```

**Verification:**
- [ ] Script correctly identifies which services use which ports
- [ ] Script provides helpful next steps

---

### Step 6: Test Stop/Start Cycles

#### 6.1 Stop Legacy Stack

```bash
docker compose -p aiavatar -f infra/compose/docker-compose.yml down
```

**Verification:**
- [ ] All `ai-avatar-*` containers stop
- [ ] `miniapp-*` containers remain running
- [ ] Port 8081 becomes free
- [ ] Port 8080 still occupied by MiniApp

#### 6.2 Stop MiniApp Stack

```bash
./scripts/miniapp-down.sh
```

**Verification:**
- [ ] All `miniapp-*` containers stop
- [ ] Port 8080 becomes free
- [ ] Can restart either stack independently

#### 6.3 Restart Both

```bash
# Start legacy first (to test port 8080 is truly free)
docker compose -p aiavatar \
  -f infra/compose/docker-compose.yml \
  --env-file infra/compose/.env.mainstack \
  up -d

# Start MiniApp
./scripts/miniapp-up.sh
```

**Verification:**
- [ ] Legacy starts on 8081 without trying to claim 8080
- [ ] MiniApp starts on 8080 successfully
- [ ] No port conflicts

---

### Step 7: Clean Up (Optional)

```bash
# Stop everything
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml down
docker compose -p aiavatar -f infra/compose/docker-compose.yml down

# Remove volumes (optional - will delete data)
docker volume rm aiavatar_postgres_data aiavatar_redis_data aiavatar_tts_data
```

---

## Troubleshooting

### Issue: Port 8080 Already in Use

**Symptoms:** MiniApp fails to start with "port is already allocated"

**Solution:**
```bash
# Find what's using port 8080
./scripts/ports-diagnose.sh

# If it's legacy API:
docker compose -p aiavatar -f infra/compose/docker-compose.yml down

# If it's another process on Windows:
netstat -ano | findstr :8080
taskkill /PID <pid> /F

# If it's another process on Linux:
lsof -i :8080
kill <pid>
```

### Issue: Legacy API Tries to Use Port 8080

**Symptoms:** `docker-compose.yml` still binds to 8080

**Solution:**
```bash
# Verify docker-compose.yml has the change:
grep -A2 "ai-avatar-api" infra/compose/docker-compose.yml | grep ports

# Should show:
#   - "${AI_AVATAR_API_PORT:-8081}:8080"

# Verify .env.mainstack has:
grep AI_AVATAR_API_PORT infra/compose/.env.mainstack
# Should show: AI_AVATAR_API_PORT=8081

# If not, file may need to be recreated
```

### Issue: Website Can't Connect to API

**Symptoms:** Website loads but API calls fail

**Solution:**
```bash
# Check PUBLIC_API_BASE_URL in .env.mainstack:
grep PUBLIC_API_BASE_URL infra/compose/.env.mainstack
# Should be: PUBLIC_API_BASE_URL=http://localhost:8081

# Rebuild website with correct API URL:
docker compose -p aiavatar -f infra/compose/docker-compose.yml up -d --build website
```

### Issue: "version is obsolete" Warning

**Symptoms:** Warning when starting MiniApp

**Solution:**
```bash
# Verify miniapp.compose.yaml doesn't have version key:
head -n 5 infra/compose/miniapp.compose.yaml
# Should start with "services:" NOT "version: '3.8'"

# If version is still there, remove it
```

---

## Success Criteria

All of the following should be true:

- [x] MiniApp gateway runs on port 8080
- [x] Legacy API runs on port 8081
- [x] No "version is obsolete" warning from miniapp.compose.yaml
- [x] `docker ps` shows correct port mappings (`8080->8080` for gateway, `8081->8080` for API)
- [x] Both stacks can run simultaneously without conflicts
- [x] Health checks pass for both stacks
- [x] DB and Redis remain unchanged (5432, 6379)
- [x] Diagnostics script accurately reports port usage
- [x] Wrapper scripts work on both Windows and Linux

---

## Quick Test Commands (Copy-Paste)

```bash
# Full test sequence
./scripts/ports-diagnose.sh
./scripts/miniapp-up.sh
curl http://localhost:8080/healthz
docker compose -p aiavatar -f infra/compose/docker-compose.yml --env-file infra/compose/.env.mainstack up -d --build
curl http://localhost:8081/health
docker ps | grep -E "miniapp|ai-avatar"
./scripts/ports-diagnose.sh
```

**Windows PowerShell equivalent:**
```powershell
sh ./scripts/ports-diagnose.sh
.\scripts\miniapp-up.ps1
Invoke-RestMethod -Uri "http://localhost:8080/healthz"
docker compose -p aiavatar -f infra/compose/docker-compose.yml --env-file infra/compose/.env.mainstack up -d --build
Invoke-RestMethod -Uri "http://localhost:8081/health"
docker ps
sh ./scripts/ports-diagnose.sh
```

---

## Reporting Issues

If any tests fail, collect:

1. Output of `./scripts/ports-diagnose.sh`
2. Output of `docker ps`
3. Output of `docker compose -p miniapp -f infra/compose/miniapp.compose.yaml logs`
4. Output of `docker compose -p aiavatar -f infra/compose/docker-compose.yml logs api`
5. Contents of `.env.miniapp` and `.env.mainstack` (with secrets redacted)

---

## See Also

- [PORTS.md](PORTS.md) - Port allocation policy
- [PORT_MIGRATION_CHANGELOG.md](PORT_MIGRATION_CHANGELOG.md) - Detailed change log
- [MINIAPP_QUICKSTART.md](../MINIAPP_QUICKSTART.md) - MiniApp setup guide

