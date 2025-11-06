# Cal.com Inline Embed - Unified Diffs

## A) apps/miniapp-web/index.html

```diff
--- a/apps/miniapp-web/index.html
+++ b/apps/miniapp-web/index.html
@@ -24,6 +24,66 @@
         }
       } catch (e) { console.warn('TG init skipped', e); }
     </script>
+
+    <!-- Cal.com embed loader (idempotent) -->
+    <script type="text/javascript">
+      (function (C, A, L) {
+        let p = function (a, ar) { a.q.push(ar); };
+        let d = C.document;
+        C.Cal = C.Cal || function () {
+          let cal = C.Cal, ar = arguments;
+          if (!cal.loaded) {
+            cal.ns = {}; cal.q = cal.q || [];
+            var s = d.createElement("script");
+            s.src = A; d.head.appendChild(s);
+            cal.loaded = true;
+          }
+          if (ar[0] === L) {
+            const api = function () { p(api, arguments); };
+            const namespace = ar[1];
+            api.q = api.q || [];
+            if (typeof namespace === "string") {
+              cal.ns[namespace] = cal.ns[namespace] || api;
+              p(cal.ns[namespace], ar);
+              p(cal, ["initNamespace", namespace]);
+            } else p(cal, ar);
+            return;
+          }
+          p(cal, ar);
+        };
+      })(window, "https://app.cal.com/embed/embed.js", "init");
+
+      // Init Cal.com under the 'booking' namespace
+      Cal("init", "booking", { origin: "https://cal.com" });
+
+      // Pick up VITE_CAL_LINK from script tag data attribute (injected below)
+      (function () {
+        var el = document.getElementById("cal-config");
+        var link = (el && el.dataset && el.dataset.calLink) || "dmitrybond/intro-call";
+        // Preload the meeting link for faster popup
+        // Use a small delay to ensure Cal script has processed the init queue
+        setTimeout(function() {
+          if (window.Cal && window.Cal.ns && window.Cal.ns["booking"]) {
+            Cal.ns["booking"]("preload", { calLink: link });
+          }
+        }, 500);
+        // Optional event hook (keep disabled by default)
+        // Cal.ns["booking"]("on", "bookingSuccessful", (payload) => { console.info("bookingSuccessful", payload); });
+      })();
+    </script>
+
+    <!-- Telegram UX nudge (safe no-op outside Telegram) -->
+    <script>
+      if (window.Telegram && Telegram.WebApp) {
+        try { Telegram.WebApp.expand(); } catch (_) {}
+      }
+    </script>
+
+    <!-- Runtime-calibrated data from Vite env -->
+    <script id="cal-config" type="application/json"
+            data-cal-link="%VITE_CAL_LINK%">
+    </script>
+
     <script type="module" src="/src/main.tsx"></script>
   </body>
 </html>
```

## B) apps/miniapp-web/vite.config.ts

```diff
--- a/apps/miniapp-web/vite.config.ts
+++ b/apps/miniapp-web/vite.config.ts
@@ -1,20 +1,28 @@
 import { defineConfig } from 'vite'
 import react from '@vitejs/plugin-react'
 
-export default defineConfig({
-  plugins: [react()],
+export default defineConfig(({ mode }) => {
+  const calLink = process.env.VITE_CAL_LINK || 'dmitrybond/intro-call';
+  
+  return {
+    plugins: [
+      react(),
+      {
+        name: 'html-transform',
+        transformIndexHtml(html) {
+          return html.replace(/%VITE_CAL_LINK%/g, calLink);
+        },
+      },
+    ],
   base: '/',
   build: {
     target: ['es2019','chrome80','safari13'],
     cssTarget: 'chrome80',
     outDir: 'dist',
     assetsDir: 'assets',
     manifest: true,
   },
   server: {
     host: true,
     port: 5173,
   },
   preview: {
     host: true,
     port: 5173,
   },
-})
+  };
+})
```

## C) apps/miniapp-web/src/vite-env.d.ts

```diff
--- a/apps/miniapp-web/src/vite-env.d.ts
+++ b/apps/miniapp-web/src/vite-env.d.ts
@@ -1,12 +1,18 @@
 /// <reference types="vite/client" />
 
+interface ImportMetaEnv {
+  readonly VITE_CAL_LINK?: string;
+}
+
+interface ImportMeta {
+  readonly env: ImportMetaEnv;
+}
+
 declare global {
   interface Window {
     Telegram?: {
       WebApp?: {
         ready: () => void
         expand: () => void
         openTgLink?: (url: string) => void
       }
     }
   }
 }
 
 export {}
```

## D) apps/miniapp-web/src/components/Buttons.tsx

```diff
--- a/apps/miniapp-web/src/components/Buttons.tsx
+++ b/apps/miniapp-web/src/components/Buttons.tsx
@@ -1,20 +1,18 @@
-import { getCal } from "../api/client";
-
 type Props = {
   onSkills: () => void;
   onTasks: () => void;
 };
 
 export function PrimaryActions({ onSkills, onTasks }: Props) {
-  const onBook = async () => {
-    try {
-      const { url } = await getCal();
-      window.open(url, "_blank");
-    } catch {
-      window.open("https://cal.com/dmitrybond/intro-30m", "_blank");
-    }
-  };
+  const calLink = import.meta.env.VITE_CAL_LINK || "dmitrybond/intro-call";
 
   return (
     <div className="grid grid-cols-1 gap-2">
-      <button className="h-12 rounded bg-black text-white" onClick={onBook}>Book a meeting</button>
+      <button
+        id="book-meeting"
+        className="h-12 rounded bg-black text-white"
+        data-cal-link={calLink}
+        data-cal-namespace="booking"
+        data-cal-config='{"layout":"month_view","theme":"auto"}'
+      >
+        Book a meeting
+      </button>
       <button className="h-12 rounded bg-gray-100" onClick={onSkills}>What I can do?</button>
       <button className="h-12 rounded bg-gray-100" onClick={onTasks}>Task status</button>
     </div>
   );
 }
```

## E) apps/miniapp-web/env.example

```diff
--- a/apps/miniapp-web/env.example
+++ b/apps/miniapp-web/env.example
@@ -1,2 +1,5 @@
 VITE_API_BASE_URL=https://miniapp.dmitrybond.tech
 VITE_DEFAULT_LANG=ru
 
+# Cal.com meeting slug (namespace: booking)
+VITE_CAL_LINK=dmitrybond/intro-call
+
```

