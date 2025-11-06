# Brief Upload 404 Fix - Unified Diff

## File: apps/miniapp-web/nginx/default.conf

```diff
--- a/apps/miniapp-web/nginx/default.conf
+++ b/apps/miniapp-web/nginx/default.conf
@@ -26,13 +26,19 @@
   }
 
   location /briefs/ {
+    proxy_request_buffering off;
     proxy_pass http://api:8080/briefs/;
     proxy_set_header Host $host;
     proxy_set_header X-Real-IP $remote_addr;
     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     proxy_set_header X-Forwarded-Proto $scheme;
+    proxy_read_timeout 300s;
+    proxy_connect_timeout 60s;
   }
 
   location /api/briefs/ {
+    proxy_request_buffering off;
     proxy_pass http://api:8080/briefs/;
     proxy_set_header Host $host;
     proxy_set_header X-Real-IP $remote_addr;
     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     proxy_set_header X-Forwarded-Proto $scheme;
+    proxy_read_timeout 300s;
+    proxy_connect_timeout 60s;
   }
```

## File: apps/api/src/app/main.py

```diff
--- a/apps/api/src/app/main.py
+++ b/apps/api/src/app/main.py
@@ -20,9 +20,9 @@
     """Application lifespan manager."""
     # Startup
     logger.info("Starting API server...")
-    # Sanity-check presence of Notion env vars without logging secrets
+    # Sanity-check presence of Notion and Telegram env vars without logging secrets
     import os as _os
-    for k in ("NOTION_API_KEY", "NOTION_PUBLIC_TASKS_DB_ID"):
+    for k in ("NOTION_API_KEY", "NOTION_PUBLIC_TASKS_DB_ID", "TELEGRAM_BOT_TOKEN", "TELEGRAM_ADMIN_CHAT_ID"):
         logger.info("%s present=%s", k, bool(_os.getenv(k)))
     await init_db()
```

## File: apps/api/src/app/utils/idempotency.py

```diff
--- a/apps/api/src/app/utils/idempotency.py
+++ b/apps/api/src/app/utils/idempotency.py
@@ -1,5 +1,6 @@
 """Idempotency utilities for brief uploads."""
 import os
+import asyncio
 from datetime import datetime
 from typing import Tuple, Optional
 from redis import Redis
@@ -40,28 +41,35 @@
     request_id = incoming_request_id or new_request_id()
     
     if REDIS_URL:
-        # Use Redis for idempotency
+        # Use Redis for idempotency (run in thread pool to avoid blocking)
         try:
-            r = Redis.from_url(REDIS_URL, decode_responses=True)
-            # Try to set the key (only if it doesn't exist)
-            ok = r.set(f"brief:fp:{fingerprint}", request_id, nx=True, ex=TTL_SEC)
-            
-            if ok:
-                # Successfully created new entry
-                logger.info(f"New brief fingerprint reserved: {fingerprint[:16]}... -> {request_id}")
-                return True, request_id
-            else:
-                # Key already exists, get the existing request_id
-                existing_id = r.get(f"brief:fp:{fingerprint}")
-                if existing_id:
-                    logger.info(f"Duplicate brief detected: {fingerprint[:16]}... -> {existing_id}")
-                    return False, existing_id
-                else:
-                    # Race condition: key was deleted between check and get
-                    # Try again with a new request_id
-                    request_id = new_request_id()
-                    ok = r.set(f"brief:fp:{fingerprint}", request_id, nx=True, ex=TTL_SEC)
-                    if ok:
-                        return True, request_id
-                    existing_id = r.get(f"brief:fp:{fingerprint}")
-                    return False, existing_id or request_id
+            def _redis_check():
+                r = Redis.from_url(REDIS_URL, decode_responses=True)
+                # Try to set the key (only if it doesn't exist)
+                ok = r.set(f"brief:fp:{fingerprint}", request_id, nx=True, ex=TTL_SEC)
+                
+                if ok:
+                    return True, request_id, None
+                else:
+                    # Key already exists, get the existing request_id
+                    existing_id = r.get(f"brief:fp:{fingerprint}")
+                    if existing_id:
+                        return False, existing_id, None
+                    else:
+                        # Race condition: key was deleted between check and get
+                        # Try again with a new request_id
+                        new_id = new_request_id()
+                        ok2 = r.set(f"brief:fp:{fingerprint}", new_id, nx=True, ex=TTL_SEC)
+                        if ok2:
+                            return True, new_id, None
+                        existing_id2 = r.get(f"brief:fp:{fingerprint}")
+                        return False, existing_id2 or new_id, None
+            
+            is_new, req_id, _ = await asyncio.to_thread(_redis_check)
+            if is_new:
+                logger.info(f"New brief fingerprint reserved: {fingerprint[:16]}... -> {req_id}")
+                return True, req_id
+            else:
+                logger.info(f"Duplicate brief detected: {fingerprint[:16]}... -> {req_id}")
+                return False, req_id
         except Exception as e:
             logger.warning(f"Redis idempotency failed, falling back to FS: {e}")
             # Fall through to file-based approach

