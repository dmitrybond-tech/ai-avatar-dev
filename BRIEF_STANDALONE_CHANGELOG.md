# Brief Standalone Page Implementation Changelog

## Summary
Implemented standalone `/brief` page with full RU/EN localization, iframe embedding support, and persistent nginx routing fixes.

## Changes

### Frontend (apps/miniapp-web)

#### New Files
- `apps/miniapp-web/src/pages/BriefFormPage.tsx`
  - Standalone form page component
  - Full RU/EN i18n support via URL param `?lang=ru|en`
  - Embed mode via `?embed=1` (hides header)
  - Theme override via `?theme=dark|light`
  - Auto-resize for iframe embedding (postMessage to parent)
  - WCAG 2.1 accessibility: labels, aria-invalid, aria-describedby, aria-live
  - Form validation: name, company, phone (>=7 digits), email, file
  - Toast notifications for success/error
  - Dark mode support with white text in dark forms

#### Modified Files
- `apps/miniapp-web/src/App.tsx`
  - Added `/brief` route handling
  - Standalone rendering for brief page (no wrapper)
  - Existing `?brief=1` query param still opens modal (via PrimaryActions)

- `apps/miniapp-web/nginx/default.conf`
  - Added `/api/client-log` alias proxy to API
  - Added CSP `frame-ancestors` header: `'self' https://dmitrybond.tech https://miniapp.dmitrybond.tech`
  - Existing `/client-log` and `/briefs/` routes preserved

### Backend (apps/api)

#### Modified Files
- `apps/api/src/app/main.py`
  - Updated CORS origins to include:
    - `https://miniapp.dmitrybond.tech`
    - `https://dmitrybond.tech`
    - `https://cv.dmitrybond.tech`
  - Existing origins preserved (website_origin, web.telegram.org)

- `apps/api/src/app/adapters/web/client_log.py`
  - Already has `/api/client-log` alias (no changes needed)

### Infrastructure

#### Verified Files
- `infra/compose/miniapp.final.override.yml`
  - Already mounts nginx config: `../../apps/miniapp-web/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro`
  - No changes needed

## Features

### Standalone Page
- GET `/brief` - Full standalone form page
- GET `/brief?lang=ru` - Russian locale
- GET `/brief?lang=en` - English locale
- GET `/brief?embed=1` - Embed mode (no header)
- GET `/brief?theme=dark` - Force dark theme
- GET `/brief?theme=light` - Force light theme

### Modal (Preserved)
- `?brief=1` on home page - Opens modal (existing behavior)

### API Endpoints
- POST `/briefs/upload` - Upload brief (multipart form-data)
- POST `/client-log` - Telemetry (existing)
- POST `/api/client-log` - Telemetry alias (via nginx proxy)

### Iframe Embedding
- Auto-resize via `postMessage({type:"brief:height", h: height})`
- CSP frame-ancestors allows embedding from dmitrybond.tech
- Parent site can listen for resize messages:
  ```javascript
  window.addEventListener('message', (e) => {
    if (e.data.type === 'brief:height') {
      iframe.style.height = e.data.h + 'px';
    }
  });
  ```

## Security

- File upload validation (extension whitelist, size limits) - server-side
- CSP frame-ancestors restricts embedding sources
- CORS restricted to specific domains
- Input sanitization and validation
- ARIA attributes for accessibility

## Testing Checklist

- [ ] GET `/brief` opens standalone page
- [ ] GET `/brief?lang=ru` shows Russian text
- [ ] GET `/brief?lang=en` shows English text
- [ ] GET `/brief?embed=1` hides header
- [ ] Form validation works (all required fields)
- [ ] POST `/briefs/upload` with valid data returns 200
- [ ] POST `/client-log` returns 200 {"ok":true}
- [ ] POST `/api/client-log` returns 200 {"ok":true}
- [ ] `?brief=1` on home page opens modal
- [ ] Iframe embedding works with auto-resize
- [ ] Dark mode displays correctly
- [ ] Accessibility: screen reader compatible

## Commit Message

```
feat(web): standalone /brief page (embeddable) + i18n + dark-form a11y

- Add BriefFormPage component with full RU/EN localization
- Support ?lang, ?embed, ?theme URL params
- Auto-resize for iframe embedding via postMessage
- WCAG 2.1 accessibility: labels, aria-invalid, aria-live
- Dark mode support with white text in dark forms

fix(web): nginx proxy /client-log and /briefs + CSP frame-ancestors

- Add /api/client-log alias proxy to API
- Add CSP frame-ancestors header for iframe embedding
- Preserve existing /client-log and /briefs/ routes

chore(api): CORS allowlist + /api/client-log alias

- Add dmitrybond.tech, miniapp.dmitrybond.tech, cv.dmitrybond.tech to CORS
- /api/client-log alias already exists in client_log.py
```

