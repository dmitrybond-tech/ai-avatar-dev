# Telegram Export Verification Runbook

## Prerequisites

- `curl` or PowerShell `Invoke-WebRequest`
- `jq` (optional, for JSON formatting)
- Python 3.x with `requests` (for large payload test)

## Base URL

```bash
BASE="https://miniapp.dmitrybond.tech"
# Or for local testing:
# BASE="http://localhost:8000"
```

## Test 1: Telegram Selftest (GET)

### Bash

```bash
curl -sS "$BASE/api/telegram/selftest" | jq .
```

### PowerShell

```powershell
$base = "https://miniapp.dmitrybond.tech"
Invoke-RestMethod -Uri "$base/api/telegram/selftest" -Method Get | ConvertTo-Json -Depth 10
```

### Expected Results

**Success (200):**
```json
{
  "ok": true,
  "bot": {
    "id": 123456789,
    "is_bot": true,
    "first_name": "Bot Name",
    "username": "bot_username"
  }
}
```

**Missing Env (400):**
```json
{
  "detail": "TELEGRAM_TOKEN is not set"
}
```

## Test 2: Small Transcript Export (POST)

### Bash

```bash
curl -sS -X POST "$BASE/api/export/telegram" \
  -H "Content-Type: application/json" \
  -d '{
    "conv_id": "test-small",
    "lang": "ru",
    "messages": [
      {"role": "user", "content": "Привет"},
      {"role": "assistant", "content": "Здравствуйте! Чем могу помочь?"}
    ]
  }' | jq .
```

### PowerShell

```powershell
$body = @{
    conv_id = "test-small"
    lang = "ru"
    messages = @(
        @{role = "user"; content = "Привет"},
        @{role = "assistant"; content = "Здравствуйте! Чем могу помочь?"}
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "$base/api/export/telegram" -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10
```

### Expected Result (200)

```json
{
  "ok": true,
  "sent": {
    "method": "sendMessage",
    "parts": 1
  }
}
```

## Test 3: Large Transcript Export (POST)

### Python Script

```python
import requests
import json

base = "https://miniapp.dmitrybond.tech"
big_content = "line\n" * 3000

payload = {
    "conv_id": "test-large",
    "lang": "ru",
    "messages": [
        {"role": "user", "content": big_content}
    ]
}

response = requests.post(
    f"{base}/api/export/telegram",
    json=payload,
    timeout=60
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
```

### PowerShell (Alternative)

```powershell
$bigContent = ("line`n" * 3000)
$body = @{
    conv_id = "test-large"
    lang = "ru"
    messages = @(
        @{role = "user"; content = $bigContent}
    )
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$base/api/export/telegram" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 60
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)"
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    $reader.ReadToEnd() | ConvertFrom-Json | ConvertTo-Json -Depth 10
}
```

### Expected Result (200)

```json
{
  "ok": true,
  "message_id": 12345,
  "sent": {
    "method": "sendDocument"
  }
}
```

## Test 4: Missing Env Variables (Error Handling)

### Test with Missing Token

If `TELEGRAM_TOKEN` is not set, expect:

```json
{
  "detail": "TELEGRAM_TOKEN or ADMIN_CHAT_ID is not set"
}
```

Status: `400 Bad Request`

### Test with Invalid Token

If token is invalid, expect:

```json
{
  "detail": "Telegram request failed: RuntimeError: Telegram error: {...}"
}
```

Status: `502 Bad Gateway`

## Test 5: Backward Compatibility (items vs messages)

### Test with `items` field

```bash
curl -sS -X POST "$BASE/api/export/telegram" \
  -H "Content-Type: application/json" \
  -d '{
    "conv_id": "test-items",
    "lang": "en",
    "items": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hi there!"}
    ]
  }' | jq .
```

Should work the same as `messages` field.

## UI Verification

1. Open the miniapp in Telegram WebView
2. Start a conversation (send a few messages)
3. Click "Завершить и отправить в Telegram" button
4. Verify:
   - Button shows "Отправляю…" while sending
   - Success message appears: "Отправила переписку в Telegram."
   - Check Network tab: POST to `/api/export/telegram` returns 200
   - Check Telegram admin chat: transcript received

## Troubleshooting

### 502 Bad Gateway

- Check `TELEGRAM_TOKEN` is set and valid
- Check `ADMIN_CHAT_ID` is set and valid
- Check network connectivity to `api.telegram.org`
- Check API logs: `docker compose logs api`

### 400 Bad Request

- Verify env variables are set in compose file
- Check API logs for validation errors
- Verify payload shape matches expected format

### No Message Received

- Verify `ADMIN_CHAT_ID` is correct (numeric chat ID)
- Check Telegram bot has permission to send messages
- Verify bot is not blocked by admin user
- Check API logs for Telegram API errors
