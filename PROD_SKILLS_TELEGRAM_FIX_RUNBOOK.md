# Production Skills & Telegram Export Fix - Validation Runbook

This runbook validates that all fixes are working correctly. Supports both PowerShell (Windows) and Bash (Linux).

## Prerequisites

- API service running and accessible
- Base URL: `https://miniapp.dmitrybond.tech` (production) or `http://localhost:8000` (local)
- `curl` or `Invoke-WebRequest` (PowerShell) available

## Validation Steps

### 1. Verify OpenAPI Schema Exposes Required Routes

**PowerShell:**
```powershell
$baseUrl = "https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
$openapi = Invoke-RestMethod -Uri "$baseUrl/api/openapi.json" -Method Get

# Check for required paths
$requiredPaths = @("/api/skills/debug", "/api/telegram/selftest")
foreach ($path in $requiredPaths) {
    $found = $openapi.paths.PSObject.Properties.Name | Where-Object { $_ -like "*$path*" }
    if ($found) {
        Write-Host "✓ Found route: $path" -ForegroundColor Green
    } else {
        Write-Host "✗ Missing route: $path" -ForegroundColor Red
        exit 1
    }
}
Write-Host "`nAll required routes found in OpenAPI schema" -ForegroundColor Green
```

**Bash:**
```bash
BASE_URL="https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
OPENAPI=$(curl -s "$BASE_URL/api/openapi.json")

for path in "/api/skills/debug" "/api/telegram/selftest"; do
    if echo "$OPENAPI" | grep -q "\"$path\""; then
        echo "✓ Found route: $path"
    else
        echo "✗ Missing route: $path"
        exit 1
    fi
done
echo ""
echo "All required routes found in OpenAPI schema"
```

### 2. Test `/api/skills/debug` Endpoint

**PowerShell:**
```powershell
$baseUrl = "https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
$response = Invoke-RestMethod -Uri "$baseUrl/api/skills/debug" -Method Get

# Validate response structure
if ($response.provider -and $response.count -ge 1) {
    Write-Host "✓ /api/skills/debug returns valid data" -ForegroundColor Green
    Write-Host "  Provider: $($response.provider)" -ForegroundColor Cyan
    Write-Host "  Count: $($response.count)" -ForegroundColor Cyan
    Write-Host "  CSV exists: $($response.csv_exists)" -ForegroundColor Cyan
} else {
    Write-Host "✗ /api/skills/debug returned invalid data" -ForegroundColor Red
    Write-Host "  Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Yellow
    exit 1
}
```

**Bash:**
```bash
BASE_URL="https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
RESPONSE=$(curl -s "$BASE_URL/api/skills/debug")

# Check if response has required fields
if echo "$RESPONSE" | grep -q '"provider"' && echo "$RESPONSE" | grep -q '"count"'; then
    COUNT=$(echo "$RESPONSE" | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    if [ "$COUNT" -ge 1 ]; then
        echo "✓ /api/skills/debug returns valid data"
        echo "$RESPONSE" | jq '{provider, count, csv_exists}'
    else
        echo "✗ /api/skills/debug returned count < 1"
        echo "$RESPONSE" | jq .
        exit 1
    fi
else
    echo "✗ /api/skills/debug returned invalid response"
    echo "$RESPONSE"
    exit 1
fi
```

### 3. Test `/api/skills?lang=ru` Endpoint

**PowerShell:**
```powershell
$baseUrl = "https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
$response = Invoke-RestMethod -Uri "$baseUrl/api/skills?lang=ru" -Method Get

if ($response.Count -ge 1) {
    Write-Host "✓ /api/skills?lang=ru returns $($response.Count) items" -ForegroundColor Green
    Write-Host "  First item: $($response[0].slug)" -ForegroundColor Cyan
} else {
    Write-Host "✗ /api/skills?lang=ru returned 0 items" -ForegroundColor Red
    exit 1
}
```

**Bash:**
```bash
BASE_URL="https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
RESPONSE=$(curl -s "$BASE_URL/api/skills?lang=ru")

COUNT=$(echo "$RESPONSE" | jq 'length')
if [ "$COUNT" -ge 1 ]; then
    echo "✓ /api/skills?lang=ru returns $COUNT items"
    echo "$RESPONSE" | jq '.[0] | {slug, title}'
else
    echo "✗ /api/skills?lang=ru returned 0 items"
    echo "$RESPONSE"
    exit 1
fi
```

### 4. Test `/api/telegram/selftest` Endpoint

**PowerShell:**
```powershell
$baseUrl = "https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/telegram/selftest" -Method Get
    if ($response.ok -and $response.bot) {
        Write-Host "✓ /api/telegram/selftest returns bot info" -ForegroundColor Green
        Write-Host "  Bot username: $($response.bot.username)" -ForegroundColor Cyan
    } else {
        Write-Host "✗ /api/telegram/selftest returned invalid response" -ForegroundColor Red
        exit 1
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 400) {
        Write-Host "⚠ /api/telegram/selftest returned 400 (expected if TELEGRAM_TOKEN missing)" -ForegroundColor Yellow
        Write-Host "  This is acceptable if Telegram is not configured" -ForegroundColor Yellow
    } else {
        Write-Host "✗ /api/telegram/selftest failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}
```

**Bash:**
```bash
BASE_URL="https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
HTTP_CODE=$(curl -s -o /tmp/selftest_response.json -w "%{http_code}" "$BASE_URL/api/telegram/selftest")

if [ "$HTTP_CODE" -eq 200 ]; then
    RESPONSE=$(cat /tmp/selftest_response.json)
    if echo "$RESPONSE" | grep -q '"ok":true' && echo "$RESPONSE" | grep -q '"bot"'; then
        echo "✓ /api/telegram/selftest returns bot info"
        echo "$RESPONSE" | jq '{ok, bot: .bot.username}'
    else
        echo "✗ /api/telegram/selftest returned invalid response"
        echo "$RESPONSE"
        exit 1
    fi
elif [ "$HTTP_CODE" -eq 400 ]; then
    echo "⚠ /api/telegram/selftest returned 400 (expected if TELEGRAM_TOKEN missing)"
    echo "  This is acceptable if Telegram is not configured"
else
    echo "✗ /api/telegram/selftest failed with HTTP $HTTP_CODE"
    cat /tmp/selftest_response.json
    exit 1
fi
```

### 5. Test `/api/export/telegram` with Small Payload

**PowerShell:**
```powershell
$baseUrl = "https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
$smallPayload = @{
    messages = @(
        @{ role = "user"; content = "Hello" }
        @{ role = "assistant"; content = "Hi there!" }
    )
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/export/telegram" -Method Post -Body $smallPayload -ContentType "application/json"
    if ($response.ok -and $response.sent.method -eq "sendMessage") {
        Write-Host "✓ /api/export/telegram (small) returns 200 with sendMessage" -ForegroundColor Green
    } else {
        Write-Host "✗ /api/export/telegram (small) returned unexpected response" -ForegroundColor Red
        Write-Host "  Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Yellow
        exit 1
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 400) {
        Write-Host "⚠ /api/export/telegram returned 400 (expected if TELEGRAM_TOKEN/ADMIN_CHAT_ID missing)" -ForegroundColor Yellow
    } else {
        Write-Host "✗ /api/export/telegram failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}
```

**Bash:**
```bash
BASE_URL="https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
SMALL_PAYLOAD='{"messages":[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hi there!"}]}'

HTTP_CODE=$(curl -s -o /tmp/export_small.json -w "%{http_code}" \
    -X POST "$BASE_URL/api/export/telegram" \
    -H "Content-Type: application/json" \
    -d "$SMALL_PAYLOAD")

if [ "$HTTP_CODE" -eq 200 ]; then
    RESPONSE=$(cat /tmp/export_small.json)
    if echo "$RESPONSE" | grep -q '"ok":true' && echo "$RESPONSE" | grep -q '"sendMessage"'; then
        echo "✓ /api/export/telegram (small) returns 200 with sendMessage"
        echo "$RESPONSE" | jq '{ok, sent}'
    else
        echo "✗ /api/export/telegram (small) returned unexpected response"
        echo "$RESPONSE"
        exit 1
    fi
elif [ "$HTTP_CODE" -eq 400 ]; then
    echo "⚠ /api/export/telegram returned 400 (expected if TELEGRAM_TOKEN/ADMIN_CHAT_ID missing)"
else
    echo "✗ /api/export/telegram failed with HTTP $HTTP_CODE"
    cat /tmp/export_small.json
    exit 1
fi
```

### 6. Test `/api/export/telegram` with Large Payload

**PowerShell:**
```powershell
$baseUrl = "https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
# Create large payload (>3500 chars to trigger sendDocument)
$largeContent = "This is a test message. " * 200  # ~5000 chars
$largePayload = @{
    messages = @(
        @{ role = "user"; content = $largeContent }
        @{ role = "assistant"; content = "Response to large message" }
    )
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/export/telegram" -Method Post -Body $largePayload -ContentType "application/json"
    if ($response.ok -and $response.sent.method -eq "sendDocument") {
        Write-Host "✓ /api/export/telegram (large) returns 200 with sendDocument" -ForegroundColor Green
    } else {
        Write-Host "✗ /api/export/telegram (large) returned unexpected response" -ForegroundColor Red
        Write-Host "  Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor Yellow
        exit 1
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 400) {
        Write-Host "⚠ /api/export/telegram returned 400 (expected if TELEGRAM_TOKEN/ADMIN_CHAT_ID missing)" -ForegroundColor Yellow
    } else {
        Write-Host "✗ /api/export/telegram failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}
```

**Bash:**
```bash
BASE_URL="https://miniapp.dmitrybond.tech"  # or "http://localhost:8000"
# Create large payload (>3500 chars to trigger sendDocument)
LARGE_CONTENT=$(python3 -c "print('This is a test message. ' * 200)")
LARGE_PAYLOAD=$(jq -n \
    --arg content "$LARGE_CONTENT" \
    '{messages: [{role: "user", content: $content}, {role: "assistant", content: "Response"}]}')

HTTP_CODE=$(curl -s -o /tmp/export_large.json -w "%{http_code}" \
    -X POST "$BASE_URL/api/export/telegram" \
    -H "Content-Type: application/json" \
    -d "$LARGE_PAYLOAD")

if [ "$HTTP_CODE" -eq 200 ]; then
    RESPONSE=$(cat /tmp/export_large.json)
    if echo "$RESPONSE" | grep -q '"ok":true' && echo "$RESPONSE" | grep -q '"sendDocument"'; then
        echo "✓ /api/export/telegram (large) returns 200 with sendDocument"
        echo "$RESPONSE" | jq '{ok, sent}'
    else
        echo "✗ /api/export/telegram (large) returned unexpected response"
        echo "$RESPONSE"
        exit 1
    fi
elif [ "$HTTP_CODE" -eq 400 ]; then
    echo "⚠ /api/export/telegram returned 400 (expected if TELEGRAM_TOKEN/ADMIN_CHAT_ID missing)"
else
    echo "✗ /api/export/telegram failed with HTTP $HTTP_CODE"
    cat /tmp/export_large.json
    exit 1
fi
```

## Complete Validation Script

**PowerShell (save as `validate-fix.ps1`):**
```powershell
param(
    [string]$BaseUrl = "https://miniapp.dmitrybond.tech"
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Production Skills & Telegram Export Fix Validation ===" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl`n" -ForegroundColor Cyan

# Step 1: OpenAPI
Write-Host "1. Checking OpenAPI schema..." -ForegroundColor Yellow
$openapi = Invoke-RestMethod -Uri "$BaseUrl/api/openapi.json" -Method Get
$requiredPaths = @("/api/skills/debug", "/api/telegram/selftest")
foreach ($path in $requiredPaths) {
    $found = $openapi.paths.PSObject.Properties.Name | Where-Object { $_ -like "*$path*" }
    if ($found) {
        Write-Host "   ✓ Found: $path" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Missing: $path" -ForegroundColor Red
        exit 1
    }
}

# Step 2: Skills debug
Write-Host "`n2. Testing /api/skills/debug..." -ForegroundColor Yellow
$debug = Invoke-RestMethod -Uri "$BaseUrl/api/skills/debug" -Method Get
if ($debug.count -ge 1) {
    Write-Host "   ✓ Skills count: $($debug.count)" -ForegroundColor Green
} else {
    Write-Host "   ✗ Skills count < 1" -ForegroundColor Red
    exit 1
}

# Step 3: Skills list
Write-Host "`n3. Testing /api/skills?lang=ru..." -ForegroundColor Yellow
$skills = Invoke-RestMethod -Uri "$BaseUrl/api/skills?lang=ru" -Method Get
if ($skills.Count -ge 1) {
    Write-Host "   ✓ Returns $($skills.Count) items" -ForegroundColor Green
} else {
    Write-Host "   ✗ Returns 0 items" -ForegroundColor Red
    exit 1
}

# Step 4: Telegram selftest
Write-Host "`n4. Testing /api/telegram/selftest..." -ForegroundColor Yellow
try {
    $selftest = Invoke-RestMethod -Uri "$BaseUrl/api/telegram/selftest" -Method Get
    Write-Host "   ✓ Returns bot info" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 400) {
        Write-Host "   ⚠ Returns 400 (Telegram not configured - acceptable)" -ForegroundColor Yellow
    } else {
        Write-Host "   ✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# Step 5: Export small
Write-Host "`n5. Testing /api/export/telegram (small)..." -ForegroundColor Yellow
$smallPayload = @{messages = @(@{role="user";content="Hello"},@{role="assistant";content="Hi"})} | ConvertTo-Json
try {
    $export = Invoke-RestMethod -Uri "$BaseUrl/api/export/telegram" -Method Post -Body $smallPayload -ContentType "application/json"
    Write-Host "   ✓ Returns 200" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 400) {
        Write-Host "   ⚠ Returns 400 (Telegram not configured - acceptable)" -ForegroundColor Yellow
    } else {
        Write-Host "   ✗ Failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n=== All validations passed! ===" -ForegroundColor Green
```

**Bash (save as `validate-fix.sh`):**
```bash
#!/bin/bash
set -e

BASE_URL="${1:-https://miniapp.dmitrybond.tech}"

echo ""
echo "=== Production Skills & Telegram Export Fix Validation ==="
echo "Base URL: $BASE_URL"
echo ""

# Step 1: OpenAPI
echo "1. Checking OpenAPI schema..."
OPENAPI=$(curl -s "$BASE_URL/api/openapi.json")
for path in "/api/skills/debug" "/api/telegram/selftest"; do
    if echo "$OPENAPI" | grep -q "\"$path\""; then
        echo "   ✓ Found: $path"
    else
        echo "   ✗ Missing: $path"
        exit 1
    fi
done

# Step 2: Skills debug
echo ""
echo "2. Testing /api/skills/debug..."
DEBUG=$(curl -s "$BASE_URL/api/skills/debug")
COUNT=$(echo "$DEBUG" | jq -r '.count')
if [ "$COUNT" -ge 1 ]; then
    echo "   ✓ Skills count: $COUNT"
else
    echo "   ✗ Skills count < 1"
    exit 1
fi

# Step 3: Skills list
echo ""
echo "3. Testing /api/skills?lang=ru..."
SKILLS=$(curl -s "$BASE_URL/api/skills?lang=ru")
SKILLS_COUNT=$(echo "$SKILLS" | jq 'length')
if [ "$SKILLS_COUNT" -ge 1 ]; then
    echo "   ✓ Returns $SKILLS_COUNT items"
else
    echo "   ✗ Returns 0 items"
    exit 1
fi

# Step 4: Telegram selftest
echo ""
echo "4. Testing /api/telegram/selftest..."
HTTP_CODE=$(curl -s -o /tmp/selftest.json -w "%{http_code}" "$BASE_URL/api/telegram/selftest")
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "   ✓ Returns bot info"
elif [ "$HTTP_CODE" -eq 400 ]; then
    echo "   ⚠ Returns 400 (Telegram not configured - acceptable)"
else
    echo "   ✗ Failed with HTTP $HTTP_CODE"
    exit 1
fi

# Step 5: Export small
echo ""
echo "5. Testing /api/export/telegram (small)..."
PAYLOAD='{"messages":[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hi"}]}'
HTTP_CODE=$(curl -s -o /tmp/export.json -w "%{http_code}" \
    -X POST "$BASE_URL/api/export/telegram" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")
if [ "$HTTP_CODE" -eq 200 ]; then
    echo "   ✓ Returns 200"
elif [ "$HTTP_CODE" -eq 400 ]; then
    echo "   ⚠ Returns 400 (Telegram not configured - acceptable)"
else
    echo "   ✗ Failed with HTTP $HTTP_CODE"
    exit 1
fi

echo ""
echo "=== All validations passed! ==="
```

## Usage

**PowerShell:**
```powershell
.\validate-fix.ps1
# Or with custom URL:
.\validate-fix.ps1 -BaseUrl "http://localhost:8000"
```

**Bash:**
```bash
chmod +x validate-fix.sh
./validate-fix.sh
# Or with custom URL:
./validate-fix.sh http://localhost:8000
```

## Expected Results

- ✅ All routes present in OpenAPI schema
- ✅ `/api/skills/debug` returns count ≥ 1
- ✅ `/api/skills?lang=ru` returns items ≥ 1
- ✅ `/api/telegram/selftest` returns 200 (or 400 if not configured)
- ✅ `/api/export/telegram` returns 200 (or 400 if not configured)

If all checks pass, the fixes are working correctly.
