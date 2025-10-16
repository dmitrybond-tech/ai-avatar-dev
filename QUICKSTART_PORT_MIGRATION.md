# Quick Start: Port Migration

**TL;DR:** Port 8080 is now for MiniApp, port 8081 is for Legacy API.

---

## Quick Commands

### Start MiniApp (Port 8080)

```bash
# Bash/Git Bash
./scripts/miniapp-up.sh

# PowerShell
.\scripts\miniapp-up.ps1

# Manual
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d --build

# Test
curl http://localhost:8080/healthz
```

### Start Legacy API (Port 8081)

```bash
docker compose -p aiavatar \
  -f infra/compose/docker-compose.yml \
  --env-file infra/compose/.env.mainstack \
  up -d --build

# Test
curl http://localhost:8081/health
```

### Stop Services

```bash
# MiniApp
./scripts/miniapp-down.sh  # or .\scripts\miniapp-down.ps1
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml down

# Legacy
docker compose -p aiavatar -f infra/compose/docker-compose.yml down
```

### Diagnose Ports

```bash
./scripts/ports-diagnose.sh
```

---

## Port Map

| Port | Service | URL |
|------|---------|-----|
| 8080 | MiniApp Gateway | http://localhost:8080 |
| 8081 | Legacy API | http://localhost:8081 |
| 3000 | Website | http://localhost:3000 |
| 5432 | PostgreSQL | localhost:5432 |
| 6379 | Redis | localhost:6379 |

---

## What Changed?

### ✅ Fixed
- Port 8080 freed for MiniApp (Stage-0 focus)
- Legacy API moved to 8081
- No "version is obsolete" warning
- Both stacks can run together

### 🔧 Modified Files
- `infra/compose/miniapp.compose.yaml` - Removed version key
- `infra/compose/docker-compose.yml` - Changed API port to 8081
- `scripts/miniapp-up.ps1` - Added `-p miniapp`
- `scripts/miniapp-down.ps1` - Added `-p miniapp`

### 📄 New Files
- `infra/compose/.env.miniapp` - MiniApp config
- `infra/compose/.env.mainstack` - Legacy config (8081)
- `scripts/ports-diagnose.sh` - Port checker
- `scripts/miniapp-up.sh` - Bash start script
- `scripts/miniapp-down.sh` - Bash stop script
- `docs/PORTS.md` - Port documentation

---

## Troubleshooting

### Port 8080 in use?
```bash
./scripts/ports-diagnose.sh
# Stop whatever is using it
docker compose -p aiavatar -f infra/compose/docker-compose.yml down
```

### Legacy API still on 8080?
Check that `infra/compose/.env.mainstack` has:
```ini
AI_AVATAR_API_PORT=8081
```

### "version is obsolete" warning?
Fixed! `miniapp.compose.yaml` no longer has `version:` key.

---

## One-Line Health Check

```bash
curl -s http://localhost:8080/healthz && curl -s http://localhost:8081/health && echo "Both stacks OK!"
```

---

## Full Documentation

- **Port Policy:** `docs/PORTS.md`
- **Change Log:** `docs/PORT_MIGRATION_CHANGELOG.md`
- **Testing Guide:** `docs/PORT_MIGRATION_TESTING.md`
- **Complete Deliverable:** `PORT_MIGRATION_DELIVERABLE.md`

---

**That's it! 🎉**

MiniApp owns :8080, Legacy API is on :8081, both can run together.

