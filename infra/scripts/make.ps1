# PowerShell helper script for common tasks
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('up', 'down', 'build', 'logs', 'restart', 'clean')]
    [string]$Command
)

$ComposeDir = Join-Path $PSScriptRoot "..\compose"
$ComposeFile = Join-Path $ComposeDir "docker-compose.yml"

Push-Location $ComposeDir

try {
    switch ($Command) {
        'up' {
            Write-Host "Starting all services..." -ForegroundColor Green
            docker compose -f docker-compose.yml up -d
        }
        'down' {
            Write-Host "Stopping all services..." -ForegroundColor Yellow
            docker compose -f docker-compose.yml down
        }
        'build' {
            Write-Host "Building all images..." -ForegroundColor Blue
            docker compose -f docker-compose.yml build
        }
        'logs' {
            Write-Host "Showing logs (Ctrl+C to exit)..." -ForegroundColor Cyan
            docker compose -f docker-compose.yml logs -f
        }
        'restart' {
            Write-Host "Restarting all services..." -ForegroundColor Magenta
            docker compose -f docker-compose.yml restart
        }
        'clean' {
            Write-Host "Cleaning up (removes volumes)..." -ForegroundColor Red
            $confirm = Read-Host "This will delete all data. Continue? (y/N)"
            if ($confirm -eq 'y') {
                docker compose -f docker-compose.yml down -v
                Write-Host "Cleanup complete." -ForegroundColor Green
            } else {
                Write-Host "Cancelled." -ForegroundColor Yellow
            }
        }
    }
} finally {
    Pop-Location
}

