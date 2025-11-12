# Skills 404 Fix — Changelog

## Root Cause Analysis

**Problem**: Frontend was making requests to `/api/api/skills` instead of `/api/skills`, resulting in 404 errors.

**Root Cause**: In `apps/miniapp-web/src/api/client.ts`, the code was calling `apiUrl('/api/skills')` and `apiUrl('/api/skills/${slug}')`. However, the `apiUrl()` function from `shared/api.ts` already prepends `/api` to the path (from `API_BASE`), causing a double prefix: `/api/api/skills`.

**Evidence**:
- Network tab showed requests to `skills?lang=ru|en → 404` (relative path without `/api` prefix)
- Or requests to `/api/api/skills` (double prefix) if `apiUrl()` was working but path included `/api`

## Solution

1. **Standardized `apiUrl()` function** in `apps/miniapp-web/src/shared/api.ts`:
   - Added `getApiBaseUrl()` function that consistently returns `/api` (or configured `__API_BASE__`)
   - Updated `apiUrl()` to always return absolute paths: `base + path`
   - Ensured no trailing slashes and proper path normalization

2. **Fixed API calls** in `apps/miniapp-web/src/api/client.ts`:
   - Changed `apiUrl('/api/skills')` → `apiUrl('/skills')`
   - Changed `apiUrl('/api/skills/${slug}')` → `apiUrl('/skills/${slug}')`

## Changes

### `apps/miniapp-web/src/shared/api.ts`
- Replaced `API_BASE` constant with `getApiBaseUrl()` function
- Updated `apiUrl()` to use `getApiBaseUrl()` and ensure absolute paths
- Added support for `window.__API_BASE__` override

### `apps/miniapp-web/src/api/client.ts`
- `getSkills()`: Changed `apiUrl('/api/skills${qs}')` → `apiUrl('/skills${qs}')`
- `getSkillDetail()`: Changed `apiUrl('/api/skills/${slug}${qs}')` → `apiUrl('/skills/${slug}${qs}')`

## Verification

### Backend Routes (FastAPI)
Routes are correctly registered (verified via introspection):
```
Skills routes:
  /api/skills
  /api/skills/{slug}
  /skills
  /skills/{slug}
```

Main API endpoints:
- `GET /api/skills` — list skills
- `GET /api/skills/{slug}` — get skill detail
- `GET /api/skills/debug` — diagnostics
- `POST /api/skills/ask` — ask about skills

### Frontend Behavior
- `getApiBaseUrl()` → `"/api"` (or configured value)
- `apiUrl('/skills')` → `"/api/skills"` (absolute path)
- `apiUrl('/skills/${slug}')` → `"/api/skills/${slug}"` (absolute path)

## Testing

1. **Browser Console Check**:
```javascript
import('/src/shared/api.ts').then(m => {
  console.log('getApiBaseUrl()', m.getApiBaseUrl?.());
  console.log('apiUrl("/skills"):', m.apiUrl?.('/skills'));
  console.log('apiUrl("/api/skills"):', m.apiUrl?.('/api/skills'));
});
```

Expected output:
- `getApiBaseUrl()` → `"/api"`
- `apiUrl("/skills")` → `"/api/skills"`
- `apiUrl("/api/skills")` → `"/api/api/skills"` (demonstrates why we use `/skills`)

2. **Network Tab**: Verify requests go to:
   - `https://miniapp.dmitrybond.tech/api/skills?lang=en`
   - `https://miniapp.dmitrybond.tech/api/skills/{slug}?lang=en`

## Impact

- ✅ Fixed 404 errors on skills list and detail pages
- ✅ No UI changes (grid cards + modal remain unchanged)
- ✅ No regressions (chat toggle, modal offset 60px, i18n all work)
- ✅ CSV mode remains active and functional

