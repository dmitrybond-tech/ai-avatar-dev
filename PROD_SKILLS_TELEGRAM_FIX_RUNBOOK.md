# Production Skills & Telegram Export Fix - Validation Runbook

## Prerequisites

- PowerShell or bash shell
- `curl` command available
- Access to production API endpoint (via Caddy proxy at `/api`)
- Valid `.env.miniapp` file with `TELEGRAM_TOKEN` and `ADMIN_CHAT_ID` set

## Validation Commands

### 1. Validate Skills Debug Endpoint

**Expected:** Returns 200 JSON with diagnostics (not 404)

```powershell
# PowerShell
$response = Invoke-WebRequest -Uri "https://miniapp.dmitrybond.tech/api/skills/debug" -Method GET
$response.StatusCode  # Should be 200
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Or with curl
curl -X GET "https://miniapp.dmitrybond.tech/api/skills/debug" | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Expected Response:**
```json
{
  "provider": "csv",
  "csv_path": "/app/data/skills.csv",
  "csv_exists": true,
  "notion": {
    "token": "SET|EMPTY",
    "db": "SET|EMPTY",
    "ok": true|false
  },
  "count": 10,
  "sample": [...]
}
```

**Validation:**
- Status code is 200 (not 404)
- `count` is greater than 0
- `csv_exists` is true if using CSV source

### 2. Validate Skills List Endpoint

**Expected:** Returns skills list with count ≥ 1

```powershell
# PowerShell
$response = Invoke-WebRequest -Uri "https://miniapp.dmitrybond.tech/api/skills?lang=ru" -Method GET
$data = $response.Content | ConvertFrom-Json
$data.count  # Should be >= 1
$data.items.Count  # Should be >= 1

# Or with curl
curl -X GET "https://miniapp.dmitrybond.tech/api/skills?lang=ru" | ConvertFrom-Json | Select-Object -ExpandProperty count
```

**Expected Response:**
```json
{
  "items": [
    {
      "slug": "...",
      "title": "...",
      "short": "...",
      "tags": [...]
    }
  ],
  "count": 10
}
```

**Validation:**
- `count` is greater than 0
- `items` array is not empty
- Cards render correctly in frontend

### 3. Validate Telegram Selftest Endpoint

**Expected:** Returns 200 JSON with bot info (or 400 if env missing)

```powershell
# PowerShell
try {
    $response = Invoke-WebRequest -Uri "https://miniapp.dmitrybond.tech/api/telegram/selftest" -Method GET
    $data = $response.Content | ConvertFrom-Json
    $data.ok  # Should be true
    $data.bot  # Should contain bot info
} catch {
    $_.Exception.Response.StatusCode  # Should be 400 if token missing
}

# Or with curl
curl -X GET "https://miniapp.dmitrybond.tech/api/telegram/selftest"
```

**Expected Response (Success):**
```json
{
  "ok": true,
  "bot": {
    "id": 123456789,
    "is_bot": true,
    "first_name": "...",
    "username": "..."
  }
}
```

**Expected Response (Missing Token):**
```json
{
  "detail": "TELEGRAM_TOKEN is not set"
}
```
Status: 400

**Validation:**
- Returns 200 with bot info if token is set
- Returns 400 with clear message if token is missing
- Bot info contains valid Telegram bot details

### 4. Validate Telegram Export Endpoint (Small Payload)

**Expected:** Returns 200 JSON for small payloads (uses sendMessage)

```powershell
# PowerShell
$payload = @{
    messages = @(
        @{ role = "user"; content = "Hello" }
        @{ role = "assistant"; content = "Hi there!" }
    )
    lang = "ru"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "https://miniapp.dmitrybond.tech/api/export/telegram" -Method POST -Body $payload -ContentType "application/json"
$data = $response.Content | ConvertFrom-Json
$data.ok  # Should be true
$data.sent.method  # Should be "sendMessage"

# Or with curl
$payloadJson = '{"messages":[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hi there!"}],"lang":"ru"}'
curl -X POST "https://miniapp.dmitrybond.tech/api/export/telegram" -H "Content-Type: application/json" -d $payloadJson
```

**Expected Response:**
```json
{
  "ok": true,
  "sent": {
    "method": "sendMessage",
    "parts": 1
  }
}
```

**Validation:**
- Returns 200
- `sent.method` is "sendMessage" for small payloads
- Message appears in Telegram admin chat

### 5. Validate Telegram Export Endpoint (Large Payload)

**Expected:** Returns 200 JSON for large payloads (uses sendDocument)

```powershell
# PowerShell
# Create a large message payload (>3500 chars)
$largeContent = "A" * 4000
$payload = @{
    messages = @(
        @{ role = "user"; content = $largeContent }
    )
    lang = "ru"
    title = "Large Export Test"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "https://miniapp.dmitrybond.tech/api/export/telegram" -Method POST -Body $payload -ContentType "application/json"
$data = $response.Content | ConvertFrom-Json
$data.ok  # Should be true
$data.sent.method  # Should be "sendDocument"

# Or with curl (create large payload)
$largePayload = @{
    messages = @(@{ role = "user"; content = ("A" * 4000) })
    lang = "ru"
    title = "Large Export Test"
} | ConvertTo-Json
curl -X POST "https://miniapp.dmitrybond.tech/api/export/telegram" -H "Content-Type: application/json" -d $largePayload
```

**Expected Response:**
```json
{
  "ok": true,
  "message_id": 12345,
  "sent": {
    "method": "sendDocument"
  }
}
```

**Validation:**
- Returns 200
- `sent.method` is "sendDocument" for large payloads
- Document appears in Telegram admin chat

### 6. Validate Export Handler Tolerates Both Payload Shapes

**Test with `items` field (legacy format):**

```powershell
# PowerShell
$payload = @{
    items = @(
        @{ role = "user"; content = "Test" }
        @{ role = "assistant"; content = "Response" }
    )
    lang = "ru"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "https://miniapp.dmitrybond.tech/api/export/telegram" -Method POST -Body $payload -ContentType "application/json"
$data = $response.Content | ConvertFrom-Json
$data.ok  # Should be true
```

**Validation:**
- Both `{items:[...]}` and `{messages:[...]}` formats work
- Returns 200 for valid payloads
- Returns 400 for missing env vars
- Returns 502 for network/API errors

### 7. Validate Error Handling

**Test missing env vars:**

```powershell
# This should return 400 if TELEGRAM_TOKEN or ADMIN_CHAT_ID is missing
# (Only test if you can temporarily unset env vars)
```

**Test network error (invalid token):**

```powershell
# Set invalid token temporarily and test
# Should return 502 with error details
```

**Expected Error Response:**
```json
{
  "detail": "Telegram request failed: ValueError: ..."
}
```
Status: 400 for validation errors, 502 for network/API errors

## Docker Compose Validation

### Check Environment Variables in Container

```powershell
# PowerShell
docker compose -f infra/compose/miniapp.compose.yaml exec api env | Select-String -Pattern "SKILLS_|TELEGRAM_|ADMIN_"

# Or bash
docker compose -f infra/compose/miniapp.compose.yaml exec api env | grep -E "SKILLS_|TELEGRAM_|ADMIN_"
```

**Expected Output:**
```
SKILLS_SOURCE=csv
SKILLS_CSV_PATH=/app/data/skills.csv
TELEGRAM_TOKEN=...
TELEGRAM_BOT_TOKEN=...
ADMIN_CHAT_ID=...
TELEGRAM_ADMIN_CHAT_ID=...
```

### Check CSV File Exists in Container

```powershell
# PowerShell
docker compose -f infra/compose/miniapp.compose.yaml exec api ls -la /app/data/skills.csv

# Or bash
docker compose -f infra/compose/miniapp.compose.yaml exec api test -f /app/data/skills.csv && echo "CSV exists" || echo "CSV missing"
```

**Expected:** File exists and is readable

### Optional: Mount CSV from Host (if needed)

If CSV lives on host at `/srv/ai-avatar/apps/miniapp-api/data/skills.csv`, create override:

**File:** `infra/compose/miniapp.csv.override.yml`

```yaml
services:
  api:
    volumes:
      - /srv/ai-avatar/apps/miniapp-api/data/skills.csv:/app/data/skills.csv:ro
```

Then use:
```powershell
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.csv.override.yml up -d api
```

## Acceptance Criteria Checklist

- [ ] `/api/skills/debug` returns 200 JSON with diagnostics (not 404)
- [ ] `/api/skills?lang=ru` returns count ≥ 1 (cards render)
- [ ] `/api/telegram/selftest` returns 200 JSON with bot info (or 400 if env missing)
- [ ] `/api/export/telegram` returns 200 JSON for small payloads (sendMessage)
- [ ] `/api/export/telegram` returns 200 JSON for large payloads (sendDocument)
- [ ] Export handler accepts both `{items:[...]}` and `{messages:[...]}` formats
- [ ] Error handling returns 400 for missing env vars, 502 for network errors
- [ ] No regressions: SPA deep links OK, assets 200, no CORS/mixed content

## Troubleshooting

### Skills Debug Returns 404
- Verify route order in `apps/miniapp-api/routers/skills.py` (debug before {slug})
- Restart API container: `docker compose restart api`

### Skills List Returns 0 Items
- Check `SKILLS_SOURCE` and `SKILLS_CSV_PATH` env vars in container
- Verify CSV file exists at `/app/data/skills.csv` in container
- Check container logs: `docker compose logs api | Select-String -Pattern "skills"`

### Telegram Selftest Returns 404
- Verify route exists in `apps/miniapp-api/routers/chat_v2.py`
- Verify router is included in `apps/miniapp-api/main.py`
- Restart API container

### Telegram Export Fails
- Check `TELEGRAM_TOKEN` and `ADMIN_CHAT_ID` env vars in container
- Test selftest endpoint first
- Check container logs for detailed error messages
- Verify network connectivity from container to `api.telegram.org`

