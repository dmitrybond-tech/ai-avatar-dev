# Rasa Bot Shutdown Script for Windows/PowerShell
# Stops Rasa bot services
# Usage: .\scripts\rasa-bot-down.ps1

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Rasa Bot Shutdown" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Stopping Rasa bot services..." -ForegroundColor Yellow

try {
    docker compose -f infra/compose/rasa-bot.compose.yaml down
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Services stopped successfully!" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "ERROR: Failed to stop services (exit code: $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to stop services:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

