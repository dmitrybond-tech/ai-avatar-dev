# Skills CSV Alignment Runbook

## Overview

This runbook provides PowerShell and Bash commands to verify the skills CSV loader alignment, API endpoints, and web mini-app functionality.

## Prerequisites

- Docker and Docker Compose V2 installed
- Access to the miniapp API container or local API instance
- `curl` or `Invoke-WebRequest` (PowerShell) available

## Environment Checks

### PowerShell

```powershell
# Check environment variables
Write-Host "SKILLS_SOURCE: $env:SKILLS_SOURCE"
Write-Host "SKILLS_CSV_PATH: $env:SKILLS_CSV_PATH"

# Check CSV file existence (from host)
$csvPath = if ($env:SKILLS_CSV_PATH) { $env:SKILLS_CSV_PATH } else { "apps/api/data/skills.csv" }
if (Test-Path $csvPath) {
    Write-Host "CSV file exists at: $csvPath"
    $fileInfo = Get-Item $csvPath
    Write-Host "File size: $($fileInfo.Length) bytes"
    Write-Host "Last modified: $($fileInfo.LastWriteTime)"
} else {
    Write-Host "WARNING: CSV file not found at: $csvPath"
}

# Check CSV file existence (from inside API container)
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml exec -T api sh -c "if [ -f /app/data/skills.csv ]; then echo 'CSV exists at /app/data/skills.csv'; ls -lh /app/data/skills.csv; else echo 'CSV NOT FOUND at /app/data/skills.csv'; fi"
```

### Bash

```bash
# Check environment variables
echo "SKILLS_SOURCE: ${SKILLS_SOURCE:-not set}"
echo "SKILLS_CSV_PATH: ${SKILLS_CSV_PATH:-not set}"

# Check CSV file existence (from host)
CSV_PATH="${SKILLS_CSV_PATH:-apps/api/data/skills.csv}"
if [ -f "$CSV_PATH" ]; then
    echo "CSV file exists at: $CSV_PATH"
    ls -lh "$CSV_PATH"
else
    echo "WARNING: CSV file not found at: $CSV_PATH"
fi

# Check CSV file existence (from inside API container)
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml exec -T api sh -c "if [ -f /app/data/skills.csv ]; then echo 'CSV exists at /app/data/skills.csv'; ls -lh /app/data/skills.csv; else echo 'CSV NOT FOUND at /app/data/skills.csv'; fi"
```

## API Endpoint Tests

### PowerShell

```powershell
# Set API base URL (adjust port if needed)
$apiBase = "http://localhost:18080"

# Test 1: List skills (English)
Write-Host "`n[Test 1] GET /api/skills?lang=en"
try {
    $response = Invoke-WebRequest -Uri "$apiBase/api/skills?lang=en" -Method GET -UseBasicParsing
    $data = $response.Content | ConvertFrom-Json
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Skills count: $($data.Count)"
    if ($data.Count -gt 0) {
        Write-Host "First skill: $($data[0].slug) - $($data[0].title)"
        Write-Host "Has tags: $($data[0].tags.Count -gt 0)"
    }
} catch {
    Write-Host "ERROR: $_"
}

# Test 2: List skills (Russian)
Write-Host "`n[Test 2] GET /api/skills?lang=ru"
try {
    $response = Invoke-WebRequest -Uri "$apiBase/api/skills?lang=ru" -Method GET -UseBasicParsing
    $data = $response.Content | ConvertFrom-Json
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Skills count: $($data.Count)"
    if ($data.Count -gt 0) {
        Write-Host "First skill: $($data[0].slug) - $($data[0].title)"
    }
} catch {
    Write-Host "ERROR: $_"
}

# Test 3: Get skill detail (English)
Write-Host "`n[Test 3] GET /api/skills/automation?lang=en"
try {
    $response = Invoke-WebRequest -Uri "$apiBase/api/skills/automation?lang=en" -Method GET -UseBasicParsing
    $data = $response.Content | ConvertFrom-Json
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Slug: $($data.slug)"
    Write-Host "Title: $($data.title)"
    Write-Host "Bullets count: $($data.bullets.Count)"
    Write-Host "Examples count: $($data.examples.Count)"
    if ($data.bullets.Count -gt 0) {
        Write-Host "First bullet: $($data.bullets[0].Substring(0, [Math]::Min(60, $data.bullets[0].Length)))..."
    }
} catch {
    Write-Host "ERROR: $_"
}

# Test 4: Get skill detail (Russian)
Write-Host "`n[Test 4] GET /api/skills/automation?lang=ru"
try {
    $response = Invoke-WebRequest -Uri "$apiBase/api/skills/automation?lang=ru" -Method GET -UseBasicParsing
    $data = $response.Content | ConvertFrom-Json
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Bullets count: $($data.bullets.Count)"
    Write-Host "Examples count: $($data.examples.Count)"
} catch {
    Write-Host "ERROR: $_"
}

# Test 5: Ask endpoint (requires XAI_API_KEY)
Write-Host "`n[Test 5] POST /api/skills/ask"
$body = @{
    q = "What can you help me with?"
    lang = "en"
} | ConvertTo-Json
try {
    $response = Invoke-WebRequest -Uri "$apiBase/api/skills/ask" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
    $data = $response.Content | ConvertFrom-Json
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Answer length: $($data.answer.Length)"
    Write-Host "Used skills: $($data.used_skills -join ', ')"
    Write-Host "Model: $($data.model)"
} catch {
    Write-Host "ERROR: $_ (may require XAI_API_KEY)"
}
```

### Bash

```bash
# Set API base URL (adjust port if needed)
API_BASE="http://localhost:18080"

# Test 1: List skills (English)
echo ""
echo "[Test 1] GET /api/skills?lang=en"
curl -sSf "$API_BASE/api/skills?lang=en" | jq -r '
  "Status: 200",
  "Skills count: \(length)",
  (if length > 0 then "First skill: \(.[0].slug) - \(.[0].title)" else empty end),
  (if length > 0 and (.[0].tags | length) > 0 then "Has tags: true" else empty end)
'

# Test 2: List skills (Russian)
echo ""
echo "[Test 2] GET /api/skills?lang=ru"
curl -sSf "$API_BASE/api/skills?lang=ru" | jq -r '
  "Status: 200",
  "Skills count: \(length)",
  (if length > 0 then "First skill: \(.[0].slug) - \(.[0].title)" else empty end)
'

# Test 3: Get skill detail (English)
echo ""
echo "[Test 3] GET /api/skills/automation?lang=en"
curl -sSf "$API_BASE/api/skills/automation?lang=en" | jq -r '
  "Status: 200",
  "Slug: \(.slug)",
  "Title: \(.title)",
  "Bullets count: \(.bullets | length)",
  "Examples count: \(.examples | length)",
  (if (.bullets | length) > 0 then "First bullet: \(.bullets[0][:60])..." else empty end)
'

# Test 4: Get skill detail (Russian)
echo ""
echo "[Test 4] GET /api/skills/automation?lang=ru"
curl -sSf "$API_BASE/api/skills/automation?lang=ru" | jq -r '
  "Status: 200",
  "Bullets count: \(.bullets | length)",
  "Examples count: \(.examples | length)"
'

# Test 5: Ask endpoint (requires XAI_API_KEY)
echo ""
echo "[Test 5] POST /api/skills/ask"
curl -sSf -X POST "$API_BASE/api/skills/ask" \
  -H "Content-Type: application/json" \
  -d '{"q":"What can you help me with?","lang":"en"}' | jq -r '
  "Status: 200",
  "Answer length: \(.answer | length)",
  "Used skills: \(.used_skills | join(", "))",
  "Model: \(.model)"
' || echo "ERROR: May require XAI_API_KEY"
```

## Docker Compose Commands

### Important: Include miniapp.llm.override.yml

All compose commands should include the LLM override file when using Grok integration:

```bash
# PowerShell
docker compose `
  --env-file infra/compose/.env.miniapp `
  -f infra/compose/miniapp.compose.yaml `
  -f infra/compose/miniapp.runtime.yml `
  -f infra/compose/miniapp.llm.override.yml `
  up -d

# Bash
docker compose \
  --env-file infra/compose/.env.miniapp \
  -f infra/compose/miniapp.compose.yaml \
  -f infra/compose/miniapp.runtime.yml \
  -f infra/compose/miniapp.llm.override.yml \
  up -d
```

### Check API logs for CSV loading

```bash
# PowerShell
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml logs api | Select-String -Pattern "skills|CSV"

# Bash
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml logs api | grep -i "skills\|CSV"
```

### Test from inside API container

```bash
# PowerShell
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml exec -T api sh -c "curl -sSf http://127.0.0.1:8000/api/skills?lang=en | head -c 500"

# Bash
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml exec -T api sh -c "curl -sSf http://127.0.0.1:8000/api/skills?lang=en | head -c 500"
```

## Web Mini-App Verification

### Check modal offset CSS

The web mini-app should use `modal-offset-pt` and `modal-offset-mt` classes for 60px top offset. Verify in browser DevTools:

1. Open Skills page
2. Click a skill button
3. Inspect modal element
4. Verify `padding-top: calc(env(safe-area-inset-top, 0px) + 60px)` or `margin-top: calc(env(safe-area-inset-top, 0px) + 60px)`

### Test 503 handling

If CSV file is missing, API should return 503:

```bash
# Temporarily rename CSV to test 503
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml exec -T api sh -c "mv /app/data/skills.csv /app/data/skills.csv.bak 2>/dev/null || true"

# Test endpoint
curl -sSf "$API_BASE/api/skills?lang=en" || echo "Expected 503"

# Restore CSV
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml exec -T api sh -c "mv /app/data/skills.csv.bak /app/data/skills.csv 2>/dev/null || true"
```

## Troubleshooting

### CSV not loading

1. Check `SKILLS_SOURCE` is set to `csv`
2. Verify `SKILLS_CSV_PATH` points to correct file
3. Check file permissions (readable by container user)
4. Review API logs for CSV parsing errors

### API returns empty array

1. Verify CSV headers match expected format (Title EN, Bullets EN, etc.)
2. Check CSV encoding (should be UTF-8 or UTF-8-BOM)
3. Ensure CSV has at least one valid row with title

### Modal not showing 60px offset

1. Verify `apps/miniapp-web/src/index.css` has `--modal-top-offset: calc(env(safe-area-inset-top, 0px) + 60px)`
2. Check SkillsPage.tsx uses `modal-offset-pt` and `modal-offset-mt` classes
3. Clear browser cache and rebuild web app

## Acceptance Criteria Checklist

- [ ] GET /api/skills?lang=ru returns array with slug, title, short, tags
- [ ] GET /api/skills/{slug}?lang=ru returns bullets[] and examples[]
- [ ] Web mini-app renders skills grid with clickable buttons
- [ ] Modal opens with 60px top offset
- [ ] POST /api/skills/ask works and references used_skills from CSV
- [ ] 503 error shown when CSV is missing
- [ ] No secrets in code or logs

