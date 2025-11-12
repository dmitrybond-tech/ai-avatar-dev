# Telegram Export Runbook

## Environment Variables

**Required:**
- `TELEGRAM_TOKEN` - Telegram bot token (or `TELEGRAM_BOT_TOKEN` for backward compatibility)
- `ADMIN_CHAT_ID` - Admin chat ID for receiving exports (or `TELEGRAM_ADMIN_CHAT_ID` for backward compatibility)

**Optional:**
- `TELEGRAM_TIMEOUT` - Request timeout in seconds (default: 15.0)

## Testing

### 1. Selftest (token only)

Test Telegram bot token connectivity:

```powershell
curl -sS https://miniapp.dmitrybond.tech/api/telegram/selftest | ConvertFrom-Json
```

Expected response:
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

### 2. Minimal export (token + admin chat required)

Test export with a small conversation:

```powershell
$body = @{
    title = "test"
    messages = @(
        @{ role = "user"; content = "Привет!" }
        @{ role = "assistant"; content = "Здравствуйте!" }
    )
} | ConvertTo-Json -Depth 10

curl -sS -X POST https://miniapp.dmitrybond.tech/api/export/telegram `
  -H "Content-Type: application/json" `
  -d $body | ConvertFrom-Json
```

Expected response:
```json
{
  "ok": true,
  "sent": {
    "method": "sendMessage",
    "parts": 1
  }
}
```

### 3. Large export check (forces sendDocument)

For transcripts > 3500 characters, the system automatically uses `sendDocument`:

```powershell
$bigContent = "строка`n" * 2000
$body = @{
    title = "big-test"
    messages = @(
        @{ role = "user"; content = $bigContent }
    )
} | ConvertTo-Json -Depth 10

curl -sS -X POST https://miniapp.dmitrybond.tech/api/export/telegram `
  -H "Content-Type: application/json" `
  -d $body | ConvertFrom-Json
```

Expected response:
```json
{
  "ok": true,
  "message_id": 12345,
  "sent": {
    "method": "sendDocument"
  }
}
```

### 4. Error Cases

**Missing token:**
```json
{
  "detail": "TELEGRAM_TOKEN is not set"
}
```
Status: 400 Bad Request

**Missing chat ID:**
```json
{
  "detail": "ADMIN_CHAT_ID is not set"
}
```
Status: 400 Bad Request

**Network/API errors:**
```json
{
  "detail": "Telegram request failed: ..."
}
```
Status: 502 Bad Gateway

## Implementation Notes

- **Chunking**: Messages ≤ 3500 chars use `sendMessage` with automatic chunking at 4096 chars (respecting line boundaries)
- **Large files**: Messages > 3500 chars are sent as `.txt` documents via `sendDocument`
- **Error handling**: All errors return JSON with appropriate HTTP status codes (400 for config errors, 502 for API failures)
- **Backward compatibility**: Supports both old (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`) and new (`TELEGRAM_TOKEN`, `ADMIN_CHAT_ID`) env variable names

