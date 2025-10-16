# MiniApp Dev Runbook

Complete guide for setting up and running the Telegram MiniApp development environment.

## Prerequisites

- Node.js >= 20.0.0
- pnpm >= 8.0.0
- Docker & Docker Compose (for API gateway)
- autossh (for tunnels, Linux only)

## Frontend (Astro/Vite)

### Install pnpm (if needed)

```bash
sudo npm i -g pnpm@8.15.1
```

Or check current version:

```bash
pnpm -v
```

### Start Development Server

Using the convenience script:

```bash
./scripts/dev-miniapp-frontend.sh
```

Or manually via pnpm workspace:

```bash
pnpm dev:miniapp
```

Or directly in the website directory:

```bash
cd apps/website
pnpm install
pnpm dev:miniapp
```

### Verify Frontend

The frontend should be running on `http://127.0.0.1:5173/miniapp/`

```bash
curl -I http://127.0.0.1:5173/miniapp/
```

Expected response: `200 OK`

### Configuration

- **Port**: Fixed at `5173` with `strictPort: true`
- **Base URL**: `/miniapp/`
- **Public API**: Set via `PUBLIC_GATEWAY_URL` env var (default: `https://api-miniapp.dmitrybond.tech`)

To override the API URL:

```bash
export PUBLIC_GATEWAY_URL=http://localhost:8080
pnpm dev:miniapp
```

## API Gateway (FastAPI)

### Start Gateway

```bash
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d --build gateway
```

### Verify Gateway Health

```bash
curl -s http://127.0.0.1:8080/healthz && echo
```

Expected response: `{"ok":true}`

### View Logs

```bash
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml logs -f gateway
```

### Stop Gateway

```bash
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml down
```

## Reverse Tunnels (VM → VPS)

For production deployment, reverse SSH tunnels expose local services to the VPS.

### Install Tunnels

On the VM:

```bash
USER_NAME=deploy VPS_USER=root VPS_IP=<YOUR_VPS_IP> ./infra/systemd/install-tunnels.sh
```

This will:
1. Install `autossh`
2. Configure two systemd services:
   - `miniapp-front-tunnel` (VM:5173 → VPS:15173)
   - `miniapp-api-tunnel` (VM:8080 → VPS:18080)
3. Enable and start both services

### Check Tunnel Status

```bash
systemctl status miniapp-front-tunnel
systemctl status miniapp-api-tunnel
```

### Verify on VPS

SSH into the VPS and test local tunnel endpoints:

```bash
curl -I http://127.0.0.1:15173/miniapp/
curl -s http://127.0.0.1:18080/healthz && echo
```

### Restart Tunnels

```bash
sudo systemctl restart miniapp-front-tunnel miniapp-api-tunnel
```

### View Tunnel Logs

```bash
journalctl -u miniapp-front-tunnel -f
journalctl -u miniapp-api-tunnel -f
```

## Public Domains (via Caddy on VPS)

### Setup Caddy Configuration

On the VPS:

1. Copy the Caddy include file:

```bash
scp infra/caddy/miniapp.caddy.inc root@<VPS_IP>:/etc/caddy/
```

2. Edit `/etc/caddy/Caddyfile` and add:

```
import /etc/caddy/miniapp.caddy.inc
```

3. Validate and reload Caddy:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

### Verify Public Domains

```bash
curl -I https://miniapp.dmitrybond.tech/miniapp/
curl -s https://api-miniapp.dmitrybond.tech/healthz && echo
```

Expected responses:
- Frontend: `200 OK` with HTML content
- API: `{"ok":true}`

### Caddy Logs

```bash
journalctl -u caddy -f
```

## Telegram Bot

The bot service connects users to the MiniApp.

### Configuration

Ensure `infra/compose/.env.miniapp` has the correct `WEBAPP_URL`:

```
WEBAPP_URL=https://miniapp.dmitrybond.tech/miniapp/
```

### Start Bot

```bash
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d --no-deps --force-recreate bot
```

### Verify Bot

```bash
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml logs -f bot
```

## Complete Stack Setup

To start everything at once:

### On VM (Development)

```bash
# 1. Start frontend
pnpm dev:miniapp

# 2. Start gateway (in another terminal)
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d gateway
```

### On VM (Production with Tunnels)

```bash
# 1. Install and start tunnels (one-time setup)
USER_NAME=deploy VPS_USER=root VPS_IP=<VPS_IP> ./infra/systemd/install-tunnels.sh

# 2. Start frontend
pnpm dev:miniapp

# 3. Start gateway
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d gateway

# 4. Start bot
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d bot
```

### On VPS

```bash
# Configure Caddy (one-time setup)
# Copy miniapp.caddy.inc and update Caddyfile as described above
sudo systemctl reload caddy
```

## Troubleshooting

### Frontend not accessible

```bash
# Check if port is in use
netstat -tuln | grep 5173

# Check astro process
ps aux | grep astro

# Restart with verbose logging
cd apps/website
pnpm dev:miniapp --verbose
```

### Gateway not responding

```bash
# Check container status
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml ps

# Check logs
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml logs gateway

# Rebuild and restart
docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d --build --force-recreate gateway
```

### Tunnel connection issues

```bash
# Check tunnel status
systemctl status miniapp-front-tunnel
systemctl status miniapp-api-tunnel

# Check SSH key permissions
ls -la ~/.ssh/id_ed25519
# Should be 600

# Test SSH connection manually
ssh -i ~/.ssh/id_ed25519 <VPS_USER>@<VPS_IP>

# Restart tunnels
sudo systemctl restart miniapp-front-tunnel miniapp-api-tunnel
```

### Domain not resolving

```bash
# Check DNS records
dig miniapp.dmitrybond.tech
dig api-miniapp.dmitrybond.tech

# Check Caddy configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Check Caddy logs
journalctl -u caddy -n 50

# Test tunnel endpoints on VPS
curl -v http://127.0.0.1:15173/miniapp/
curl -v http://127.0.0.1:18080/healthz
```

## Environment Variables

### Frontend (.env in apps/website/)

```bash
PUBLIC_GATEWAY_URL=https://api-miniapp.dmitrybond.tech
```

### Backend (infra/compose/.env.miniapp)

```bash
TELEGRAM_BOT_NAME=your_bot_name
TELEGRAM_TOKEN=your_bot_token
WEBAPP_URL=https://miniapp.dmitrybond.tech/miniapp/
NOTION_DB=your_notion_db_id
NOTION_SECRET=your_notion_secret
CAL_LINK=https://cal.com/youraccount
CACHE_TTL_SECONDS=600
GATEWAY_PORT=8080
```

## Acceptance Criteria

### ✅ Frontend
- [ ] `pnpm dev:miniapp` starts on `127.0.0.1:5173`
- [ ] `curl -I http://127.0.0.1:5173/miniapp/` returns `200 OK`
- [ ] Base path `/miniapp/` is correctly served
- [ ] Port 5173 is enforced (`strictPort: true`)

### ✅ Gateway
- [ ] `docker compose ... up gateway` starts successfully
- [ ] `curl http://127.0.0.1:8080/healthz` returns `{"ok":true}`
- [ ] Gateway restarts automatically (`restart: unless-stopped`)

### ✅ Tunnels
- [ ] After `install-tunnels.sh`, both services are active
- [ ] On VPS: `curl http://127.0.0.1:15173/miniapp/` returns `200 OK`
- [ ] On VPS: `curl http://127.0.0.1:18080/healthz` returns `{"ok":true}`

### ✅ Domains
- [ ] `curl https://miniapp.dmitrybond.tech/miniapp/` returns `200 OK`
- [ ] `curl https://api-miniapp.dmitrybond.tech/healthz` returns `{"ok":true}`
- [ ] HTTPS certificates are valid

### ✅ Environment
- [ ] `.env` files use LF line endings (enforced by `.gitattributes`)
- [ ] Variables are read correctly without CRLF issues
- [ ] `.sh` scripts have executable permissions

## Quick Reference

| Component | Local URL | Tunnel Port (VPS) | Public Domain |
|-----------|-----------|-------------------|---------------|
| Frontend | http://127.0.0.1:5173/miniapp/ | 15173 | https://miniapp.dmitrybond.tech/miniapp/ |
| Gateway | http://127.0.0.1:8080/healthz | 18080 | https://api-miniapp.dmitrybond.tech/healthz |

## pnpm Workspace Commands

From repository root:

```bash
# Development
pnpm dev:miniapp          # Start frontend dev server
pnpm build:miniapp        # Build frontend for production
pnpm preview:miniapp      # Preview production build

# All packages
pnpm build                # Build all packages
pnpm lint                 # Lint all packages
```

