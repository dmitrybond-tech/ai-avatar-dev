#!/usr/bin/env pwsh
# Stop Mini App services

$ErrorActionPreference = "Stop"

$composePath = "infra/compose/miniapp.compose.yaml"

Write-Host "🛑 Stopping Mini App services..." -ForegroundColor Cyan

docker compose -p miniapp -f $composePath down

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Services stopped successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to stop services" -ForegroundColor Red
    exit 1
}

Write-Host ""

