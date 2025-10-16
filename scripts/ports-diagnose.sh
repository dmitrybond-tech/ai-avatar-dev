#!/bin/sh
# Port diagnostics script for ai-avatar monorepo
# Checks common development ports and suggests next steps
#
# Usage: ./scripts/ports-diagnose.sh

set -e

echo "========================================="
echo "Port Diagnostics for AI-Avatar Monorepo"
echo "========================================="
echo ""

# Function to check port on Windows and Linux
check_port() {
    port=$1
    service_name=$2
    
    echo "Checking port $port ($service_name)..."
    
    # Try Windows netstat first (PowerShell environment)
    if command -v netstat.exe >/dev/null 2>&1; then
        result=$(netstat.exe -ano | grep ":$port " | grep LISTENING || true)
        if [ -n "$result" ]; then
            pid=$(echo "$result" | awk '{print $NF}' | head -1)
            echo "  [OCCUPIED] Port $port is in use by PID $pid"
            # Try to get process name (may fail without admin)
            if command -v tasklist.exe >/dev/null 2>&1; then
                process=$(tasklist.exe /FI "PID eq $pid" /FO CSV /NH 2>/dev/null | head -1 || true)
                if [ -n "$process" ]; then
                    echo "  Process: $process"
                fi
            fi
        else
            echo "  [FREE] Port $port is available"
        fi
    # Try Linux/Unix commands
    elif command -v ss >/dev/null 2>&1; then
        result=$(ss -tlnp 2>/dev/null | grep ":$port " || true)
        if [ -n "$result" ]; then
            echo "  [OCCUPIED] Port $port is in use"
            echo "  $result"
        else
            echo "  [FREE] Port $port is available"
        fi
    elif command -v lsof >/dev/null 2>&1; then
        result=$(lsof -i ":$port" -sTCP:LISTEN 2>/dev/null || true)
        if [ -n "$result" ]; then
            echo "  [OCCUPIED] Port $port is in use"
            echo "  $result"
        else
            echo "  [FREE] Port $port is available"
        fi
    else
        echo "  [UNKNOWN] Cannot determine port status (netstat/ss/lsof not available)"
    fi
    echo ""
}

# Check critical ports
check_port 8080 "MiniApp Gateway"
check_port 8081 "Legacy AI-Avatar API"
check_port 3000 "Website (Astro)"
check_port 5173 "Frontend Dev Server (Vite)"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"

echo "========================================="
echo "Suggested Next Steps"
echo "========================================="
echo ""
echo "1. Start MiniApp stack (gateway + bot):"
echo "   ./scripts/miniapp-up.sh"
echo "   OR (PowerShell): .\\scripts\\miniapp-up.ps1"
echo "   OR: docker compose -p miniapp -f infra/compose/miniapp.compose.yaml up -d --build"
echo ""
echo "2. Start Legacy AI-Avatar API stack:"
echo "   docker compose -p aiavatar -f infra/compose/docker-compose.yml --env-file infra/compose/.env.mainstack up -d --build"
echo ""
echo "3. Check container status:"
echo "   docker ps"
echo ""
echo "4. Test endpoints:"
echo "   curl http://localhost:8080/healthz  # MiniApp Gateway"
echo "   curl http://localhost:8081/health   # Legacy API"
echo ""
echo "For more info, see docs/PORTS.md"
echo ""

