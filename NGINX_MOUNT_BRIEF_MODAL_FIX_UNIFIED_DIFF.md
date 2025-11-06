# Unified Diff: Nginx Mount and Brief Modal Fix

## Changes

### 1. infra/compose/miniapp.final.override.yml

```diff
--- a/infra/compose/miniapp.final.override.yml
+++ b/infra/compose/miniapp.final.override.yml
@@ -35,4 +35,8 @@ services:
       - --proxy-headers
       - --forwarded-allow-ips=*
 
+  web:
+    volumes:
+      - ../../apps/miniapp-web/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
+
 
```

### 2. apps/miniapp-web/src/components/BriefUploadModal.tsx

```diff
--- a/apps/miniapp-web/src/components/BriefUploadModal.tsx
+++ b/apps/miniapp-web/src/components/BriefUploadModal.tsx
@@ -1,6 +1,5 @@
 import React, { useRef, useState, useMemo } from "react";
 import { createI18n } from "../lib/i18n";
-import { apiUrl } from "../lib/apiBase";
 
 const i18n = createI18n();
 
@@ -67,7 +66,7 @@ export function BriefUploadModal({ open, onClose }: { open: boolean; onClose: ()
       if (form.message?.trim()) {
         fd.append("message", form.message.trim());
       }
-      const res = await fetch(apiUrl("/briefs/upload"), {
+      const res = await fetch("/briefs/upload", {
         method: "POST",
         body: fd,
       });
```

## Summary

1. **Compose**: Added volume mount for nginx config to ensure proxy routes are applied at runtime
2. **Frontend**: Changed brief upload to use relative path `/briefs/upload` instead of `apiUrl("/briefs/upload")`

