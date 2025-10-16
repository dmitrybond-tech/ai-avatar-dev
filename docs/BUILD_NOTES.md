# Docker Build Troubleshooting & Network Configuration

**Date:** October 16, 2025  
**Context:** VM autobuilds for ai-avatar monorepo

---

## Problem: DNS Resolution Failures During Docker Builds

Docker builds on VMs occasionally fail with network errors:
```
Temporary failure in name resolution
Could not fetch URL https://pypi.org/simple/
ERROR: Could not find a version that satisfies the requirement fastapi
```

This happens because:
1. Docker's default DNS (8.8.8.8) may be unreachable from the VM network
2. Build containers inherit Docker daemon's DNS settings
3. Network timeouts occur without proper retry/fallback logic

---

## Solution A: Configure Docker Daemon DNS (Persistent)

**Recommended for production VMs where you have root access.**

### Steps:

1. Edit or create `/etc/docker/daemon.json`:
```json
{
  "dns": ["1.1.1.1", "8.8.8.8", "1.0.0.1"]
}
```

2. Restart Docker daemon:
```bash
sudo systemctl restart docker
```

3. Verify DNS resolution:
```bash
docker run --rm busybox nslookup pypi.org
```

**Pros:**
- ✅ Applies to all builds automatically
- ✅ No changes to build commands
- ✅ Works with Docker Compose

**Cons:**
- ❌ Requires root access
- ❌ Affects all containers on the host

---

## Solution B: Use Host Network During Build (Temporary)

**Recommended for builds where daemon config is not accessible.**

### For Docker Build:
```bash
docker build --network=host -t myimage .
```

### For Docker Buildx Bake:
```bash
docker buildx bake \
  --set miniapp-gateway.network=host \
  --set miniapp-bot.network=host \
  miniapp-gateway miniapp-bot
```

### For Docker Compose Build:
```bash
docker compose build --build-arg BUILDKIT_INLINE_CACHE=1
```
*(Then modify Dockerfile to use `RUN --network=host` for pip install)*

**Pros:**
- ✅ No daemon configuration needed
- ✅ Uses host's DNS directly
- ✅ Bypasses Docker network stack

**Cons:**
- ❌ Must be specified per build
- ❌ Requires BuildKit syntax support (`# syntax=docker/dockerfile:1.4`)

---

## Solution C: Dockerfile-Level Network Hardening (Implemented)

**Already applied to miniapp-gateway and miniapp-bot Dockerfiles.**

### Changes:
1. **Install CA certificates** (fixes SSL verification issues):
   ```dockerfile
   RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
   ```

2. **Configurable PIP index** (allows custom PyPI mirrors):
   ```dockerfile
   ARG PIP_INDEX_URL=https://pypi.org/simple
   ENV PIP_INDEX_URL=${PIP_INDEX_URL}
   ```

3. **Retry logic and timeouts**:
   ```dockerfile
   RUN python -m pip install -U pip \
    && pip install --no-cache-dir -r requirements.txt \
       -i ${PIP_INDEX_URL} \
       --retries 5 \
       --timeout 60
   ```

4. **Optional: BuildKit host-network for pip install**:
   ```dockerfile
   # syntax=docker/dockerfile:1.4
   RUN --network=host pip install --no-cache-dir -r requirements.txt \
       -i ${PIP_INDEX_URL} \
       --retries 5 \
       --timeout 60
   ```

**Pros:**
- ✅ Portable across environments
- ✅ No external configuration needed
- ✅ Fallback to custom mirrors possible

**Cons:**
- ❌ Still subject to DNS issues if host network not used

---

## Recommended Approach for VM Autobuilds

**Combine Solutions A + C:**

1. **On the VM** (one-time setup):
   - Configure Docker daemon DNS (Solution A)
   - Run diagnostic: `scripts/build-diagnose.sh`

2. **In Git post-receive hook** (per-build):
   - Use `--network=host` for Python images (Solution B)
   - Rely on Dockerfile hardening (Solution C)

Example post-receive hook:
```bash
#!/bin/bash
export PATH=/usr/local/bin:$PATH
cd /home/deployer/ai-avatar

# Pull latest code
git --work-tree=/home/deployer/ai-avatar --git-dir=/home/deployer/ai-avatar.git checkout -f

# Build Stage-0 services only (gateway + bot)
docker buildx bake \
  --set miniapp-gateway.network=host \
  --set miniapp-bot.network=host \
  --load \
  miniapp-gateway miniapp-bot

# Restart services
cd /home/deployer/ai-avatar/infra/compose
docker compose -f miniapp.compose.yaml up -d --no-build
```

---

## Website Dockerfile (Node.js/pnpm)

**Issue:** Corepack DNS lookups fail on VMs with restrictive firewalls.

**Solution:** Install pnpm via npm instead:
```dockerfile
# Before (fails on VM):
RUN corepack enable && corepack prepare pnpm@8.15.0 --activate

# After (network-robust):
RUN npm config set fund false \
 && npm config set audit false \
 && npm i -g pnpm@8.15.0
```

**Optional:** Use npm registry mirror:
```dockerfile
RUN npm config set registry https://registry.npmmirror.com \
 && npm i -g pnpm@8.15.0
```

---

## Stage-0 Build Strategy

For VM deploys, **only build services required for runtime**:

### Stage-0 Services (Required):
- ✅ `miniapp-gateway` (FastAPI)
- ✅ `miniapp-bot` (python-telegram-bot)

### Stage-1+ Services (Optional):
- ⚪ `website` (Astro frontend) - only if serving static files from VM
  - For development: use `pnpm dev` locally
  - For production: build on CI/CD, deploy to Vercel/Netlify

**Build command:**
```bash
# Explicit builds (if not using bake)
docker build --network=host -t miniapp-gateway:latest -f apps/miniapp-gateway/Dockerfile apps/miniapp-gateway
docker build --network=host -t miniapp-bot:latest -f apps/miniapp-bot/Dockerfile apps/miniapp-bot

# Or using bake targets
docker buildx bake \
  --set miniapp-gateway.network=host \
  --set miniapp-bot.network=host \
  miniapp-gateway miniapp-bot
```

---

## Diagnostics Script

Run `scripts/build-diagnose.sh` on the VM to check:
- ✅ Host DNS resolution
- ✅ Docker container DNS
- ✅ PyPI/npm registry reachability
- ✅ Docker daemon configuration

Example output:
```
=== Docker Build Diagnostics ===

[1/4] Checking host DNS...
✅ PASS: pypi.org resolves to 151.101.x.x

[2/4] Checking Docker DNS...
✅ PASS: Docker can resolve pypi.org

[3/4] Checking PyPI reachability (host network)...
✅ PASS: https://pypi.org/simple/fastapi/ is reachable

[4/4] Checking Docker daemon config...
⚠️  WARN: /etc/docker/daemon.json not found
    Consider setting custom DNS (see BUILD_NOTES.md)

=== Summary ===
✅ 3/4 checks passed
⚠️  1 warning (daemon config)

Next steps:
  1. Review warnings above
  2. If builds fail, try: docker build --network=host
  3. For persistent fix: sudo nano /etc/docker/daemon.json
```

---

## Testing on VM

### 1. Run diagnostics:
```bash
bash scripts/build-diagnose.sh
```

### 2. Test build manually:
```bash
cd apps/miniapp-gateway
docker build --network=host -t test-gateway .
```

### 3. Test via Git push:
```bash
git push vm main
# Watch logs on VM: journalctl -f -u docker
```

### 4. Verify services:
```bash
docker compose -f infra/compose/miniapp.compose.yaml ps
curl http://localhost:8080/healthz
```

---

## Alternative: Custom PyPI Mirror

If DNS issues persist, use a custom PyPI index:

### Build with custom index:
```bash
docker build \
  --network=host \
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
  -t miniapp-gateway \
  apps/miniapp-gateway
```

### Popular PyPI mirrors:
- Aliyun: `https://mirrors.aliyun.com/pypi/simple/`
- Tsinghua: `https://pypi.tuna.tsinghua.edu.cn/simple/`
- Douban: `https://pypi.doubanio.com/simple/`

---

## References

- [Docker DNS Configuration](https://docs.docker.com/config/containers/container-networking/#dns-services)
- [BuildKit Network Modes](https://docs.docker.com/engine/reference/commandline/buildx_build/#network)
- [pip Retry Logic](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-retries)

---

## Changelog

- **2025-10-16**: Initial version - DNS troubleshooting for VM autobuilds

