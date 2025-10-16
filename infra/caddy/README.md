# Caddy Configuration for MiniApp

## Setup Instructions

### 1. Copy the include file to VPS

```bash
scp infra/caddy/miniapp.caddy.inc root@YOUR_VPS_IP:/etc/caddy/
```

### 2. Update /etc/caddy/Caddyfile on VPS

Add the following line to include the MiniApp configuration:

```
import /etc/caddy/miniapp.caddy.inc
```

### 3. Test and reload Caddy

```bash
# Test configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Reload Caddy
sudo systemctl reload caddy
```

### 4. Verify the setup

```bash
# Check frontend
curl -I https://miniapp.dmitrybond.tech/miniapp/

# Check API
curl -s https://api-miniapp.dmitrybond.tech/healthz
```

## Configuration Details

- **Frontend**: `miniapp.dmitrybond.tech` → forwards to `127.0.0.1:15173` (reverse tunnel from VM:5173)
- **API Gateway**: `api-miniapp.dmitrybond.tech` → forwards to `127.0.0.1:18080` (reverse tunnel from VM:8080)

Both domains use:
- Compression (zstd, gzip)
- Automatic HTTPS with Let's Encrypt
- Static content caching (600s for frontend)

## Troubleshooting

If domains don't resolve:
1. Check DNS records point to VPS IP
2. Verify tunnels are running: `systemctl status miniapp-front-tunnel miniapp-api-tunnel`
3. Check Caddy logs: `journalctl -u caddy -f`
4. Test local tunnel endpoints:
   - `curl http://127.0.0.1:15173/miniapp/`
   - `curl http://127.0.0.1:18080/healthz`

