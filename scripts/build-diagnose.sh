#!/bin/bash
# Docker Build Diagnostics Script
# Checks DNS resolution, network connectivity, and Docker configuration for build troubleshooting
#
# Usage: bash scripts/build-diagnose.sh

set -e

echo "=== Docker Build Diagnostics ==="
echo ""

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Color codes (optional, works in most terminals)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
pass() {
  echo -e "${GREEN}✅ PASS:${NC} $1"
  ((PASS_COUNT++))
}

fail() {
  echo -e "${RED}❌ FAIL:${NC} $1"
  ((FAIL_COUNT++))
}

warn() {
  echo -e "${YELLOW}⚠️  WARN:${NC} $1"
  ((WARN_COUNT++))
}

info() {
  echo "    $1"
}

# Check 1: Host DNS resolution
echo "[1/5] Checking host DNS resolution..."
if getent hosts pypi.org >/dev/null 2>&1; then
  IP=$(getent hosts pypi.org | awk '{ print $1 }' | head -1)
  pass "pypi.org resolves to ${IP}"
else
  fail "Cannot resolve pypi.org on host"
  info "Fix: Check /etc/resolv.conf or network settings"
fi
echo ""

# Check 2: Docker container DNS
echo "[2/5] Checking Docker container DNS..."
if command -v docker >/dev/null 2>&1; then
  if docker run --rm busybox nslookup pypi.org >/dev/null 2>&1; then
    pass "Docker containers can resolve pypi.org"
  else
    fail "Docker container DNS lookup failed"
    info "Fix: Set DNS in /etc/docker/daemon.json"
    info "      See docs/BUILD_NOTES.md for details"
  fi
else
  warn "Docker command not found"
fi
echo ""

# Check 3: PyPI HTTPS reachability (host network)
echo "[3/5] Checking PyPI HTTPS reachability (host network)..."
if command -v curl >/dev/null 2>&1; then
  if curl -I -s -f --max-time 10 https://pypi.org/simple/fastapi/ >/dev/null 2>&1; then
    pass "https://pypi.org/simple/fastapi/ is reachable"
  else
    fail "Cannot reach PyPI over HTTPS"
    info "Fix: Check firewall/proxy settings"
  fi
elif command -v wget >/dev/null 2>&1; then
  if wget --spider -q --timeout=10 https://pypi.org/simple/fastapi/ 2>&1; then
    pass "https://pypi.org/simple/fastapi/ is reachable"
  else
    fail "Cannot reach PyPI over HTTPS"
    info "Fix: Check firewall/proxy settings"
  fi
else
  warn "Neither curl nor wget found, skipping HTTP check"
fi
echo ""

# Check 4: Docker daemon configuration
echo "[4/5] Checking Docker daemon configuration..."
if [ -f /etc/docker/daemon.json ]; then
  if grep -q '"dns"' /etc/docker/daemon.json 2>/dev/null; then
    DNS_CONFIG=$(grep -A 3 '"dns"' /etc/docker/daemon.json | head -4)
    pass "Docker daemon has custom DNS configured"
    info "Current DNS config:"
    echo "${DNS_CONFIG}" | sed 's/^/      /'
  else
    warn "/etc/docker/daemon.json exists but no DNS config found"
    info "Consider adding: {\"dns\": [\"1.1.1.1\", \"8.8.8.8\"]}"
  fi
else
  warn "/etc/docker/daemon.json not found"
  info "Docker is using default DNS settings"
  info "Consider creating config: sudo nano /etc/docker/daemon.json"
  info "  {\"dns\": [\"1.1.1.1\", \"8.8.8.8\", \"1.0.0.1\"]}"
fi
echo ""

# Check 5: BuildKit support
echo "[5/5] Checking Docker BuildKit support..."
if command -v docker >/dev/null 2>&1; then
  DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+' | head -1)
  MAJOR=$(echo $DOCKER_VERSION | cut -d. -f1)
  MINOR=$(echo $DOCKER_VERSION | cut -d. -f2)
  
  if [ "$MAJOR" -gt 18 ] || ([ "$MAJOR" -eq 18 ] && [ "$MINOR" -ge 9 ]); then
    pass "Docker $DOCKER_VERSION supports BuildKit"
    info "You can use: docker build --network=host"
  else
    warn "Docker $DOCKER_VERSION may not support BuildKit network modes"
    info "Consider upgrading to Docker 18.09+"
  fi
else
  warn "Docker not found"
fi
echo ""

# Summary
echo "=== Summary ==="
echo "✅ Passed: ${PASS_COUNT}"
[ $WARN_COUNT -gt 0 ] && echo "⚠️  Warnings: ${WARN_COUNT}"
[ $FAIL_COUNT -gt 0 ] && echo "❌ Failed: ${FAIL_COUNT}"
echo ""

# Recommendations
if [ $FAIL_COUNT -gt 0 ]; then
  echo "=== Action Required ==="
  echo "1. Review failed checks above"
  echo "2. If DNS issues persist, try building with: docker build --network=host"
  echo "3. For persistent fix, configure Docker daemon DNS (see BUILD_NOTES.md)"
  echo ""
elif [ $WARN_COUNT -gt 0 ]; then
  echo "=== Recommendations ==="
  echo "1. Review warnings above"
  echo "2. Consider configuring Docker daemon DNS for more robust builds"
  echo "3. Read docs/BUILD_NOTES.md for detailed solutions"
  echo ""
else
  echo "=== All Checks Passed! ==="
  echo "Your environment is configured correctly for Docker builds."
  echo ""
fi

# Exit with error if any check failed
[ $FAIL_COUNT -eq 0 ] && exit 0 || exit 1

