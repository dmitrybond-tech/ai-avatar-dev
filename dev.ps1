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
