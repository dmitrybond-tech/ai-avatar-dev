# Cal.com Inline Embed Implementation - Changelog

## Summary
Enabled the "Book a meeting" button to open a Cal.com popup modal inline inside the Telegram WebApp webview without navigation. The solution is minimal, dependency-free, and idempotent.

## Changes

### 1. `apps/miniapp-web/index.html`
**Added Cal.com embed loader with idempotent initialization**

- Added Cal.com embed bootstrap script before `</body>`
- Implemented idempotent loader that prevents duplicate script loads on HMR
- Initialized Cal.com under 'booking' namespace with origin configuration
- Added script to read `VITE_CAL_LINK` from data attribute and preload the meeting link
- Added Telegram WebApp expand call for better UX (safe no-op in regular browsers)
- Added `cal-config` script tag with `%VITE_CAL_LINK%` placeholder for build-time replacement

**Key features:**
- Idempotent: Uses `Cal.loaded` flag to prevent duplicate loads
- Preloads meeting link for faster popup
- Includes commented event hook example for `bookingSuccessful` event
- Safe no-op Telegram expand call

### 2. `apps/miniapp-web/vite.config.ts`
**Added HTML transform plugin to inject environment variable**

- Modified config to use function form to access `process.env`
- Added custom `html-transform` plugin that replaces `%VITE_CAL_LINK%` placeholder in HTML
- Reads `VITE_CAL_LINK` from environment with fallback to `dmitrybond/intro-call`

### 3. `apps/miniapp-web/src/vite-env.d.ts`
**Extended TypeScript definitions for VITE_CAL_LINK**

- Added `ImportMetaEnv` interface with `VITE_CAL_LINK?: string`
- Added `ImportMeta` interface extension for type safety
- Maintains existing Telegram WebApp type definitions

### 4. `apps/miniapp-web/src/components/Buttons.tsx`
**Replaced onClick handler with Cal.com data attributes**

- Removed `getCal` import (no longer needed)
- Removed `onBook` async handler that opened new window
- Added `calLink` constant reading from `import.meta.env.VITE_CAL_LINK` with fallback
- Updated button to include Cal.com data attributes:
  - `data-cal-link={calLink}`
  - `data-cal-namespace="booking"`
  - `data-cal-config='{"layout":"month_view","theme":"auto"}'`
- Added `id="book-meeting"` for potential future reference
- Button now relies on Cal.com embed script for automatic binding (no onClick handler)

### 5. `apps/miniapp-web/env.example`
**Added VITE_CAL_LINK configuration example**

- Added comment explaining Cal.com meeting slug configuration
- Added `VITE_CAL_LINK=dmitrybond/intro-call` as example value

## Technical Details

### Idempotency
The Cal.com embed loader uses a `Cal.loaded` flag to prevent duplicate script loads. This ensures:
- No duplicate script tags on HMR
- No duplicate initialization on page refresh
- Safe to call multiple times

### Environment Variable Flow
1. Build time: `vite.config.ts` reads `process.env.VITE_CAL_LINK`
2. HTML transform: Replaces `%VITE_CAL_LINK%` in `index.html`
3. Runtime: `cal-config` script tag contains the actual value
4. React component: Reads from `import.meta.env.VITE_CAL_LINK` (also build-time replaced)

### Cal.com Embed Binding
- Cal.com embed script automatically binds to buttons with:
  - `data-cal-link` attribute
  - `data-cal-namespace` attribute
- No manual event handlers needed
- Works with dynamically rendered React components

### Telegram WebApp Compatibility
- Added `Telegram.WebApp.expand()` call for better UX
- Safe no-op in regular browsers (guarded with existence checks)
- Works inline within Telegram WebApp webview (no navigation)

## Testing Checklist

- [ ] Clicking "Book a meeting" opens Cal.com modal overlay (no page navigation)
- [ ] Works in regular desktop browser
- [ ] Works inside Telegram WebApp webview
- [ ] No duplicate script loads on HMR
- [ ] No console errors
- [ ] Link is configurable via `VITE_CAL_LINK` environment variable
- [ ] Default fallback works (`dmitrybond/intro-call`)
- [ ] No regressions to existing features (Skills, Tasks, Chat)

## Files Modified

1. `apps/miniapp-web/index.html` - Added Cal.com embed loader
2. `apps/miniapp-web/vite.config.ts` - Added HTML transform plugin
3. `apps/miniapp-web/src/vite-env.d.ts` - Added VITE_CAL_LINK type
4. `apps/miniapp-web/src/components/Buttons.tsx` - Updated button with Cal.com attributes
5. `apps/miniapp-web/env.example` - Added VITE_CAL_LINK example

## Notes

- No new NPM dependencies added
- No file/folder structure changes
- No changes to routing or base paths
- No modifications to Notion/Skills/other app features
- CSP changes not required (documented as optional if needed in the future)

## Optional CSP Headers (if needed)

If strict CSP blocks the popup, add these headers (not applied by default):

```
script-src https://app.cal.com https://cal.com
frame-src https://app.cal.com https://cal.com
connect-src https://*.cal.com
img-src https://*.cal.com data:
style-src 'self' 'unsafe-inline'
```


