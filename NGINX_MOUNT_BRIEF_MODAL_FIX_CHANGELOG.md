# Changelog: Nginx Mount and Brief Modal Fix

## Summary
Fixed nginx routing by mounting default.conf via compose volume, and ensured Brief modal always renders with proper error handling.

## Changes

### 1. Compose: Mount nginx config into web container
**File**: `infra/compose/miniapp.final.override.yml`

Added volume mount for nginx configuration to ensure the proxy routes are applied at runtime:
- Mounts `apps/miniapp-web/nginx/default.conf` to `/etc/nginx/conf.d/default.conf` as read-only
- This ensures the nginx config with `/client-log` and `/briefs/` proxy routes is always used, regardless of Dockerfile COPY

```yaml
  web:
    volumes:
      - ../../apps/miniapp-web/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
```

### 2. Frontend: Use relative path for brief upload
**File**: `apps/miniapp-web/src/components/BriefUploadModal.tsx`

Changed from `apiUrl("/briefs/upload")` to relative path `/briefs/upload`:
- Removed unused `apiUrl` import
- Now uses relative path that will be proxied by nginx to `http://api:8080/briefs/upload`
- Ensures consistent routing through nginx proxy

### 3. Verified existing implementations

#### Nginx config (`apps/miniapp-web/nginx/default.conf`)
✅ Already contains correct proxy routes:
- `location = /client-log` → proxies to `http://api:8080/client-log`
- `location /briefs/` → proxies to `http://api:8080/briefs/`

#### Client logging (`apps/miniapp-web/src/lib/clientLog.ts`)
✅ Already uses `/client-log` and swallows all errors (best-effort logging)

#### Brief modal (`apps/miniapp-web/src/components/BriefUploadModal.tsx`)
✅ Already has all required features:
- Close button (✕) in top-right corner
- ErrorBoundary to prevent blank screens
- All required fields: name, company, phone, email, message (optional), file
- Proper validation for email and phone
- Backdrop click to close
- Deep-link support via `?brief=1` query parameter

## Testing

### Acceptance Criteria

1. **Nginx proxy routes work**:
   ```bash
   curl -sS -X POST https://miniapp.dmitrybond.tech/client-log \
     -H 'content-type: application/json' \
     -d '{"level":"info","message":"ok"}' 
   # Expected: {"ok":true}
   ```

2. **Brief upload works**:
   ```bash
   curl -sS -F "name=Test" -F "company=Acme" \
     -F "phone=+1234567" -F "email=test@example.com" \
     -F "message=Hi" -F "file=@/etc/hosts" \
     https://miniapp.dmitrybond.tech/briefs/upload
   # Expected: {"ok":true,...} and Telegram admin gets digest + file
   ```

3. **Modal in browser/Telegram WebView**:
   - Modal always visible when clicking "Brief for Estimate / Загрузить ТЗ…"
   - Modal can be closed via ✕ button or backdrop click
   - Validation works (required fields, email format, phone format)
   - File upload works
   - Deep-link `?brief=1` auto-opens modal

## Files Changed

1. `infra/compose/miniapp.final.override.yml` - Added web service volume mount
2. `apps/miniapp-web/src/components/BriefUploadModal.tsx` - Changed to relative path, removed unused import

## Notes

- The nginx config was already correct; the issue was that it wasn't being mounted at runtime
- The Brief modal already had all required features from previous work
- No new dependencies added
- No routes changed (kept `/client-log` and `/briefs/upload`)
- Cal.com embed remains unchanged

