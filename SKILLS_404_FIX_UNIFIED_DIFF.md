# Skills 404 Fix — Unified Diff

## Changes

### `apps/miniapp-web/src/shared/api.ts`

```diff
-export const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");
-
-export const apiUrl = (path: string) =>
-  `${API_BASE}${path.startsWith("/") ? path : "/" + path}`;
+export function getApiBaseUrl(): string {
+  try {
+    const raw = (window as any).__API_BASE__ || import.meta.env.VITE_API_BASE_URL || "/api";
+    return String(raw).replace(/\/+$/, ""); // без хвостового '/'
+  } catch {
+    return "/api";
+  }
+}
+
+export function apiUrl(p: string): string {
+  const base = getApiBaseUrl();                          // напр. '/api'
+  const path = ("/" + String(p || "").trim()).replace(/\/+/, "/");
+  return base + path;                                    // всегда абсолютный: '/api/skills'
+}
```

### `apps/miniapp-web/src/api/client.ts`

```diff
 export async function getSkills(lang: Locale, signal?: AbortSignal): Promise<SkillCard[]> {
   const qs = `?lang=${lang}`;
-  const r = await fetch(apiUrl(`/api/skills${qs}`), {
+  const r = await fetch(apiUrl(`/skills${qs}`), {
     signal,
     headers: {
       "X-Locale": lang,
       "Accept-Language": lang,
     },
   });
   ...
 }

 export async function getSkillDetail(slug: string, lang: Locale, signal?: AbortSignal): Promise<SkillDetail> {
   const qs = `?lang=${lang}`;
-  const r = await fetch(apiUrl(`/api/skills/${encodeURIComponent(slug)}${qs}`), {
+  const r = await fetch(apiUrl(`/skills/${encodeURIComponent(slug)}${qs}`), {
     signal,
     headers: {
       "X-Locale": lang,
       "Accept-Language": lang,
     },
   });
   ...
 }
```

## Summary

- **2 files changed**
- **5 lines removed, 15 lines added**
- **Net change: +10 lines**

### Key Changes:
1. Replaced `API_BASE` constant with `getApiBaseUrl()` function for runtime flexibility
2. Standardized `apiUrl()` to always return absolute paths
3. Fixed double `/api` prefix issue by removing `/api` from path arguments
4. Added support for `window.__API_BASE__` override

