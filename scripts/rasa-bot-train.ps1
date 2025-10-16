# Rasa Bot Training Script for Windows/PowerShell
# Trains the Rasa model using Docker
# Usage: .\scripts\rasa-bot-train.ps1

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Rasa Bot Training Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if rasa folder exists
$rasaPath = "apps\rasa-bot\rasa"
if (-Not (Test-Path $rasaPath)) {
    Write-Host "ERROR: Rasa folder not found at $rasaPath" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found Rasa folder at $rasaPath" -ForegroundColor Green

# Get absolute path for volume mount
$absoluteRasaPath = (Resolve-Path $rasaPath).Path

Write-Host ""
Write-Host "Starting training..." -ForegroundColor Yellow
Write-Host "This may take several minutes depending on your machine." -ForegroundColor Yellow
Write-Host ""

# Run training
try {
    docker run --rm -v "${absoluteRasaPath}:/app" rasa/rasa:3.6.20 train --fixed-model-name rasa-bot-model
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "==================================" -ForegroundColor Green
        Write-Host "✓ Training completed successfully!" -ForegroundColor Green
        Write-Host "==================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Model saved to: $rasaPath\models" -ForegroundColor Cyan
        
        # List models
        if (Test-Path "$rasaPath\models") {
            Write-Host ""
            Write-Host "Available models:" -ForegroundColor Cyan
            Get-ChildItem "$rasaPath\models" | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor White }
        }
    } else {
        Write-Host ""
        Write-Host "ERROR: Training failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "ERROR: Training failed with exception:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run .\scripts\rasa-bot-dev.ps1 to start the bot" -ForegroundColor White
Write-Host "  2. Test the bot in Telegram" -ForegroundColor White
Write-Host ""

