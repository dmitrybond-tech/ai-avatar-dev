# Rasa Bot Development Startup Script for Windows/PowerShell
# Starts Rasa bot services using Docker Compose
# Usage: .\scripts\rasa-bot-dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Rasa Bot Development Startup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env.rasa-bot exists, if not copy from example
$envFile = ".env.rasa-bot"
$envExample = ".env.rasa-bot.example"

if (-Not (Test-Path $envFile)) {
    Write-Host "⚠ Environment file not found. Creating from example..." -ForegroundColor Yellow
    
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "✓ Created $envFile from $envExample" -ForegroundColor Green
        Write-Host ""
        Write-Host "IMPORTANT: Please fill in the following values in $envFile" -ForegroundColor Yellow
        Write-Host ""
        
        # Prompt for required values
        $telegramToken = Read-Host "Enter TELEGRAM_TOKEN (from @BotFather)"
        $telegramBotName = Read-Host "Enter TELEGRAM_BOT_NAME (bot username without @)"
        $notionSecret = Read-Host "Enter NOTION_SECRET (Notion integration secret)"
        $notionDb = Read-Host "Enter NOTION_DB (Notion database ID)"
        $calLink = Read-Host "Enter CAL_LINK (optional calendar link, press Enter to skip)"
        
        # Update .env file
        $envContent = Get-Content $envFile
        $envContent = $envContent -replace "TELEGRAM_TOKEN=", "TELEGRAM_TOKEN=$telegramToken"
        $envContent = $envContent -replace "TELEGRAM_BOT_NAME=", "TELEGRAM_BOT_NAME=$telegramBotName"
        $envContent = $envContent -replace "NOTION_SECRET=", "NOTION_SECRET=$notionSecret"
        $envContent = $envContent -replace "NOTION_DB=", "NOTION_DB=$notionDb"
        if ($calLink) {
            $envContent = $envContent -replace "CAL_LINK=", "CAL_LINK=$calLink"
        }
        $envContent | Set-Content $envFile
        
        Write-Host ""
        Write-Host "✓ Environment file configured" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Example file $envExample not found" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Found environment file: $envFile" -ForegroundColor Green
}

# Check if model exists
$modelPath = "apps\rasa-bot\rasa\models"
if (-Not (Test-Path $modelPath) -or (Get-ChildItem $modelPath -Filter *.tar.gz -ErrorAction SilentlyContinue).Count -eq 0) {
    Write-Host ""
    Write-Host "⚠ No trained model found!" -ForegroundColor Yellow
    Write-Host "You need to train the model first using:" -ForegroundColor Yellow
    Write-Host "  .\scripts\rasa-bot-train.ps1" -ForegroundColor White
    Write-Host ""
    $response = Read-Host "Continue without trained model? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Exiting. Please train the model first." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Write-Host "Starting Rasa bot services..." -ForegroundColor Yellow

# Start services
try {
    docker compose -f infra/compose/rasa-bot.compose.yaml up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Services started successfully!" -ForegroundColor Green
        Write-Host ""
        
        # Wait for services to be ready
        Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        # Check Rasa version
        Write-Host ""
        Write-Host "Verifying Rasa installation:" -ForegroundColor Cyan
        docker exec rasa-bot rasa --version
        
        Write-Host ""
        Write-Host "==================================" -ForegroundColor Green
        Write-Host "✓ Rasa Bot is running!" -ForegroundColor Green
        Write-Host "==================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Services:" -ForegroundColor Cyan
        Write-Host "  - Rasa API:        http://localhost:5005" -ForegroundColor White
        Write-Host "  - Action Server:   http://localhost:5055" -ForegroundColor White
        Write-Host ""
        Write-Host "To enable Telegram polling:" -ForegroundColor Cyan
        Write-Host "  docker exec -it rasa-bot rasa run --connector telegram --port 5005" -ForegroundColor White
        Write-Host ""
        Write-Host "Useful commands:" -ForegroundColor Cyan
        Write-Host "  View logs:       docker compose -f infra/compose/rasa-bot.compose.yaml logs -f" -ForegroundColor White
        Write-Host "  Stop services:   .\scripts\rasa-bot-down.ps1" -ForegroundColor White
        Write-Host "  Shell access:    docker exec -it rasa-bot bash" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "ERROR: Failed to start services (exit code: $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to start services:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

