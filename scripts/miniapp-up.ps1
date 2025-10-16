#!/usr/bin/env pwsh
# Start Mini App services (gateway + bot)

$ErrorActionPreference = "Stop"

$envPath = "infra/compose/.env.miniapp"
$examplePath = "env.miniapp.example"
$composePath = "infra/compose/miniapp.compose.yaml"

Write-Host "🚀 Starting Mini App services..." -ForegroundColor Cyan

# Check if .env.miniapp exists, if not copy from example
if (-not (Test-Path $envPath)) {
    Write-Host "📋 .env.miniapp not found. Copying from example..." -ForegroundColor Yellow
    
    if (Test-Path $examplePath) {
        Copy-Item $examplePath $envPath
        Write-Host "✅ Created $envPath" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  IMPORTANT: Please edit $envPath and set your configuration:" -ForegroundColor Yellow
        Write-Host "   - TELEGRAM_TOKEN (from @BotFather)" -ForegroundColor Yellow
        Write-Host "   - NOTION_DB (your Notion database ID)" -ForegroundColor Yellow
        Write-Host "   - NOTION_SECRET (your Notion integration secret)" -ForegroundColor Yellow
        Write-Host "   - WEBAPP_URL (URL where frontend will run)" -ForegroundColor Yellow
        Write-Host "   - CAL_LINK (your booking calendar link)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "After configuration, run this script again." -ForegroundColor Cyan
        exit 0
    } else {
        Write-Host "❌ Error: $examplePath not found!" -ForegroundColor Red
        exit 1
    }
}

# Start services with Docker Compose
Write-Host "🐳 Building and starting containers..." -ForegroundColor Cyan
docker compose -p miniapp -f $composePath up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start services" -ForegroundColor Red
    exit 1
}

# Wait a moment for services to initialize
Start-Sleep -Seconds 3

# Check gateway health
Write-Host ""
Write-Host "🔍 Checking gateway health..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/healthz" -Method Get -TimeoutSec 5
    if ($response.ok -eq $true) {
        Write-Host "✅ Gateway is healthy!" -ForegroundColor Green
        Write-Host ""
        Write-Host "🎉 Mini App services are running!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📡 Gateway API: http://localhost:8080" -ForegroundColor Cyan
        Write-Host "   - GET  /healthz" -ForegroundColor Gray
        Write-Host "   - POST /reply {text}" -ForegroundColor Gray
        Write-Host "   - POST /refresh" -ForegroundColor Gray
        Write-Host ""
        Write-Host "🤖 Telegram bot is polling..." -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To stop: .\scripts\miniapp-down.ps1" -ForegroundColor Yellow
    } else {
        Write-Host "⚠️  Gateway responded but health check failed" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not reach gateway health endpoint" -ForegroundColor Yellow
    Write-Host "   Services may still be starting up. Check logs with:" -ForegroundColor Gray
        Write-Host "   docker compose -p miniapp -f $composePath logs -f" -ForegroundColor Gray
}

Write-Host ""

