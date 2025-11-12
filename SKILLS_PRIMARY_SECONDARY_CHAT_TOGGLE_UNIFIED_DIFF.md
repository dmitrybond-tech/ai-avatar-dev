# Skills Primary/Secondary + Chat Toggle Wiring - Unified Diff

## New File: `apps/miniapp-web/src/shared/skillsAdapter.ts`

```diff
+/**
+ * Skills API data adapter - normalizes API responses to UI model.
+ * Tolerant to legacy fields (key/name/summary) but outputs unified format.
+ */
+
+export type SkillListItem = {
+  slug: string;
+  title: string;
+  short: string;
+  tags: string[];
+};
+
+export type SkillDetail = SkillListItem & {
+  bullets: string[];
+  examples: string[];
+};
+
+/**
+ * Map API list response to SkillListItem array.
+ * Handles both array and {items,count} shapes.
+ */
+export function mapList(api: any[]): SkillListItem[] {
+  return (api ?? [])
+    .map((x) => ({
+      slug: String(x.slug ?? x.key ?? "").trim(),
+      title: String(x.title ?? x.name ?? "").trim(),
+      short: String(x.short ?? x.summary ?? "").trim(),
+      tags: Array.isArray(x.tags) ? x.tags : [],
+    }))
+    .filter((x) => x.slug && x.title);
+}
+
+/**
+ * Map API detail response to SkillDetail.
+ * Tolerant to legacy field names.
+ */
+export function mapDetail(x: any): SkillDetail {
+  return {
+    slug: String(x.slug ?? x.key ?? "").trim(),
+    title: String(x.title ?? x.name ?? "").trim(),
+    short: String(x.short ?? x.summary ?? "").trim(),
+    tags: Array.isArray(x.tags) ? x.tags : [],
+    bullets: Array.isArray(x.bullets) ? x.bullets : [],
+    examples: Array.isArray(x.examples) ? x.examples : [],
+  };
+}
```

---

## Modified: `apps/miniapp-web/src/api/client.ts`

```diff
 import { apiFetch, getApiBaseUrl } from "../lib/api.ts";
 import { apiUrl } from "../shared/api.ts";
 import type { Locale } from "../shared/i18n/resolveLocale";
+import { mapList, mapDetail } from "../shared/skillsAdapter.ts";
 import type {
   TasksStatusResponse,
   CalLinkResponse,
   ChatConfig,
   ChatAskPayload,
   ChatExportPayload,
   ChatAskResponse,
   SkillCard,
   SkillDetail,
   ChatMessageDto,
 } from "../types";

 ...

 export async function getSkills(lang: Locale, signal?: AbortSignal): Promise<SkillCard[]> {
   const qs = `?lang=${lang}`;
-  const r = await fetch(apiUrl(`/skills${qs}`), {
+  const r = await fetch(apiUrl(`/api/skills${qs}`), {
     signal,
     headers: {
       "X-Locale": lang,
       "Accept-Language": lang,
     },
   });
   if (!r.ok) {
     throw new Error(`Failed to load skills (status ${r.status})`);
   }
   const data = await r.json();
   // Guard: handle both array and {items,count} shapes
   const items = Array.isArray(data) ? data : (data?.items || []);
-  if (!Array.isArray(items)) {
-    return [];
-  }
-  return items
-    .map((item) => ({
-      slug: typeof item?.slug === "string" ? item.slug : "",
-      title: typeof item?.title === "string" ? item.title : "",
-      short: typeof item?.short === "string" ? item.short : "",
-      tags: ensureStringArray(item?.tags),
-    }))
-    .filter((item) => item.slug && item.title);
+  return mapList(items);
 }

 export async function getSkillDetail(slug: string, lang: Locale, signal?: AbortSignal): Promise<SkillDetail> {
   const qs = `?lang=${lang}`;
-  const r = await fetch(apiUrl(`/skills/${encodeURIComponent(slug)}${qs}`), {
+  const r = await fetch(apiUrl(`/api/skills/${encodeURIComponent(slug)}${qs}`), {
     signal,
     headers: {
       "X-Locale": lang,
       "Accept-Language": lang,
     },
   });
   if (!r.ok) {
     throw new Error(`Skill ${slug} not found (status ${r.status})`);
   }
   const payload = await r.json();
-  return {
-    slug: typeof payload?.slug === "string" ? payload.slug : slug,
-    title: typeof payload?.title === "string" ? payload.title : slug,
-    short: typeof payload?.short === "string" ? payload.short : undefined,
-    tags: ensureStringArray(payload?.tags),
-    bullets: ensureStringArray(payload?.bullets),
-    examples: ensureStringArray(payload?.examples),
-  };
+  return mapDetail(payload);
 }
```

---

## Modified: `apps/miniapp-web/src/pages/SkillsPage.tsx`

```diff
           <div
             ref={dialogRef}
             role="dialog"
             aria-modal="true"
             aria-label={activeDetail?.title ?? selectedSlug ?? titles[lang]}
             tabIndex={-1}
-            className="relative modal-maxh w-full overflow-auto max-w-lg rounded-3xl bg-white p-5 shadow-xl focus-visible:outline-none"
-            style={{ marginTop: '60px' }}
+            className="relative modal-offset-mt modal-maxh w-full overflow-auto max-w-lg rounded-3xl bg-white p-5 shadow-xl focus-visible:outline-none"
             onClick={(event) => event.stopPropagation()}
           >
```

---

## Modified: `apps/miniapp-web/src/components/SkillDetail.tsx`

```diff
       {skill.bullets?.length ? (
         <section className="space-y-2">
           <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
-            {sectionLabels.bullets[lang]}
+            {lang === 'ru' ? 'Что делаю' : 'What I do'}
           </h2>
-          <ul className="list-disc space-y-2 pl-5 text-sm leading-relaxed text-gray-800">
+          <ul className="space-y-2 text-sm leading-relaxed text-gray-800">
             {skill.bullets.map((line, index) => (
-              <li key={index}>{line}</li>
+              <li key={index} className="flex items-start gap-2">
+                <span className="mt-1 flex-shrink-0 text-gray-400">✓</span>
+                <span>{line}</span>
+              </li>
             ))}
           </ul>
         </section>
       ) : null}

       {skill.examples?.length ? (
         <section className="space-y-2">
           <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
-            {sectionLabels.examples[lang]}
+            {lang === 'ru' ? 'Примеры' : 'Examples'}
           </h2>
           <div className="space-y-2 text-sm leading-relaxed text-gray-700">
             {skill.examples.map((example, index) => (
-              <p key={index}>{example}</p>
+              <p key={index} className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
+                {example}
+              </p>
             ))}
           </div>
         </section>
       ) : null}
```

---

## Summary

- **New file:** `skillsAdapter.ts` - Data normalization adapter
- **Modified:** `client.ts` - Use adapter, fix API paths (`/api/skills`)
- **Modified:** `SkillsPage.tsx` - Use CSS class for modal offset
- **Modified:** `SkillDetail.tsx` - Checklist bullets, card-style examples

**Total:** 1 new file, 3 modified files

