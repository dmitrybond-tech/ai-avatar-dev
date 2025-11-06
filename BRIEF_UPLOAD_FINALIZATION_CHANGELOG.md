# Brief Upload Finalization Changelog

## Summary

Finalized file upload functionality for briefs with unified API routes, nginx proxy configuration, Telegram + Notion integration, and idempotency support. Updated frontend to show request_id and lock re-submit on success.

## Changes

### 1. Nginx Configuration (`apps/miniapp-web/nginx/default.conf`)

- **Replaced** two separate location blocks (`/briefs/` and `/api/briefs/`) with a single regex location pattern
- **Updated** to use `location ~ ^/(api/)?briefs/` that matches both `/briefs/` and `/api/briefs/`
- **Changed** `proxy_pass` to `http://api:8080` (without trailing path) to preserve the original request path
- **Maintained** all proxy settings: `proxy_request_buffering off`, headers, and timeouts

### 2. Frontend - BriefUploadModal (`apps/miniapp-web/src/components/BriefUploadModal.tsx`)

- **Added** state management for `submittedId` and `submitStatus`
- **Updated** submit handler to:
  - Try `/briefs/upload` first, fallback to `/api/briefs/upload` if needed
  - Parse response to extract `request_id` and `dedup` flag
  - Show success message with request_id
  - Display copy button for request_id
  - Lock form fields and submit button after successful submission
  - Handle duplicate submissions (show dedup message, don't reset form)
- **Added** success/error status display with copy-to-clipboard functionality
- **Disabled** all form inputs when `submittedId` is set
- **Updated** button text to show "Submitted" state when locked

### 3. Notion Service (`apps/api/src/app/services/notion.py`)

- **Fixed** Status property type from `select` to `status` to match Notion database schema
- **Changed** `"Status": {"select": {"name": "Backlog"}}` to `"Status": {"status": {"name": "Backlog"}}`

### 4. API Routes (Already Implemented)

- Both `/briefs/upload` and `/api/briefs/upload` routes are correctly registered in `main.py`
- Single handler `_upload_brief_handler` processes both routes
- Idempotency, Telegram, and Notion integration already functional

## Technical Details

### Nginx Regex Location

The regex pattern `^/(api/)?briefs/` matches:
- `/briefs/upload` → proxied to `http://api:8080/briefs/upload`
- `/api/briefs/upload` → proxied to `http://api:8080/api/briefs/upload`

The `proxy_pass http://api:8080` (without trailing slash) preserves the original request path.

### Idempotency

- Uses Redis SETNX for distributed idempotency (with FS fallback)
- Fingerprint computed as: `sha256(email|name|company|phone|file_hash)`
- Returns same `request_id` with `dedup: true` on duplicate submissions
- TTL: 15 minutes (configurable via `BRIEF_IDEMPOTENCY_TTL`)

### Telegram Integration

- Sends document to `TELEGRAM_ADMIN_CHAT_ID` via `sendDocument` API
- Caption includes: locale, name, company, phone, email, optional comment, request_id
- HTML-formatted caption with proper escaping

### Notion Integration

- Creates page in `NOTION_PUBLIC_TASKS_DB_ID` database
- Properties:
  - Name: `"Brief | {company} | {name}"`
  - Status: `"Backlog"` (status type)
  - Request ID: rich_text
  - Email: email
  - Phone: phone_number
  - Locale: select
  - Source: `"Miniapp Brief"` (select)
  - Comment: rich_text

## Testing

### Acceptance Criteria

1. ✅ Both API routes accessible:
   - `curl -X POST http://api:8080/briefs/upload ...` → 200
   - `curl -X POST http://api:8080/api/briefs/upload ...` → 200

2. ✅ Idempotency:
   - First request → `{"ok": true, "request_id": "...", "dedup": false}`
   - Duplicate request → `{"ok": true, "request_id": "...", "dedup": true}`

3. ✅ Telegram:
   - Admin receives document with caption
   - File descriptor properly closed

4. ✅ Notion:
   - New page created in Backlog with request_id
   - All fields populated correctly

5. ✅ Frontend:
   - Form submits successfully
   - Request ID displayed with copy button
   - Form locked after submission
   - Duplicate submissions handled gracefully

### Verification Commands

```bash
# Check API routes
python -c 'from app.main import app; print([r.path for r in app.routes if "brief" in r.path])'

# Test upload (first time)
curl -X POST http://localhost:8080/briefs/upload \
  -F "file=@test.pdf" \
  -F "locale=en" \
  -F "name=Test User" \
  -F "company=Test Co" \
  -F "phone=+1234567890" \
  -F "email=test@example.com"

# Test duplicate (should return same request_id with dedup:true)
curl -X POST http://localhost:8080/briefs/upload \
  -F "file=@test.pdf" \
  -F "locale=en" \
  -F "name=Test User" \
  -F "company=Test Co" \
  -F "phone=+1234567890" \
  -F "email=test@example.com"
```

## Files Modified

1. `apps/miniapp-web/nginx/default.conf` - Unified regex location for briefs
2. `apps/miniapp-web/src/components/BriefUploadModal.tsx` - Request ID display and form locking
3. `apps/api/src/app/services/notion.py` - Fixed Status property type

## Files Already Implemented (No Changes)

1. `apps/api/src/app/adapters/web/briefs.py` - Upload handler with idempotency
2. `apps/api/src/app/utils/idempotency.py` - Redis/FS idempotency logic
3. `apps/api/src/app/services/telegram.py` - Telegram document sending
4. `apps/api/src/app/main.py` - Route registration
5. `apps/miniapp-web/src/pages/BriefFormPage.tsx` - Standalone brief page (already has request_id support)

## Environment Variables

Required environment variables (already documented):
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `TELEGRAM_ADMIN_CHAT_ID` - Admin chat ID for brief notifications
- `NOTION_API_KEY` - Notion integration token
- `NOTION_PUBLIC_TASKS_DB_ID` - Notion database ID for briefs
- `REDIS_URL` - Redis connection URL (optional, falls back to FS)
- `DATA_DIR` - Data directory for uploads (default: `/data`)
- `MAX_UPLOAD_MB` - Max upload size in MB (default: 64)
- `BRIEF_IDEMPOTENCY_TTL` - Idempotency TTL in seconds (default: 900)

## Notes

- Preserved existing i18n support
- Preserved standalone `/brief` page functionality
- Preserved inline embed in mini-app
- No PII logging (only request_id and metadata)
- File uploads saved to `/data/uploads/{request_id}/{filename}`
- Max upload size: 64 MB
- Allowed extensions: images, PDF, DOC/DOCX, TXT, ZIP

