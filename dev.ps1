Param(
    [Parameter(Position=0)][string]$task
)

switch ($task) {
    'api' {
        Write-Host "Starting API (FastAPI) on http://127.0.0.1:8080" -ForegroundColor Green
        uvicorn apps.miniapp_api.main:app --host 127.0.0.1 --port 8080 --reload
    }
    'bot' {
        Write-Host "Starting Telegram bot (aiogram)" -ForegroundColor Green
        python .\apps\miniapp-bot\main.py
    }
    'web' {
        Write-Host "Starting Web (Vite dev server) on http://127.0.0.1:5173" -ForegroundColor Green
        Push-Location apps\miniapp-web
        npm ci
        npm run dev
        Pop-Location
    }
    Default {
        Write-Host "Usage: pwsh ./dev.ps1 [api|bot|web]" -ForegroundColor Yellow
    }
}
param(
    [Parameter(Mandatory=$true)][ValidateSet('bot','api','web')]
    [string]$Task
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Start-Bot {
    $projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $botDir = Join-Path $projectRoot 'apps\miniapp-bot'
    $venvDir = Join-Path $botDir '.venv'

    if (-not (Test-Path $venvDir)) {
        Write-Host 'Creating virtualenv for bot...'
        python -m venv $venvDir
    }

    $pip = Join-Path $venvDir 'Scripts\pip.exe'
    $python = Join-Path $venvDir 'Scripts\python.exe'

    Push-Location $botDir
    try {
        & $pip install --disable-pip-version-check -r requirements.txt
        & $python .\main.py
    } finally {
        Pop-Location
    }
}

function Start-Api {
    $projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $apiModule = 'apps.miniapp_api.main:app'
    Write-Host 'Starting API with uvicorn...'
    uvicorn $apiModule --host 127.0.0.1 --port 8080 --reload
}

function Start-Web {
    $projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $webDir = Join-Path $projectRoot 'apps\miniapp-web'
    Push-Location $webDir
    try {
        if (Test-Path 'package-lock.json') { Remove-Item 'package-lock.json' -Force }
        npm ci
        npm run dev
    } finally {
        Pop-Location
    }
}

switch ($Task) {
    'bot' { Start-Bot }
    'api' { Start-Api }
    'web' { Start-Web }
}
