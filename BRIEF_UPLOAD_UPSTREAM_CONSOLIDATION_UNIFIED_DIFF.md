# Brief Upload Upstream Consolidation - Unified Diff

## File: apps/miniapp-web/nginx/default.conf

```diff
--- a/apps/miniapp-web/nginx/default.conf
+++ b/apps/miniapp-web/nginx/default.conf
@@
-  location ~ ^/(api/)?briefs/ {
-    proxy_request_buffering off;
-    proxy_pass http://api:8080;
+  location /briefs/ {
+    client_max_body_size 64m;
+    proxy_request_buffering off;
+    proxy_pass http://api:8080/briefs/;
     proxy_set_header Host $host;
     proxy_set_header X-Real-IP $remote_addr;
     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     proxy_set_header X-Forwarded-Proto $scheme;
     proxy_read_timeout 300s;
     proxy_connect_timeout 60s;
   }
+
+  location /api/briefs/ {
+    client_max_body_size 64m;
+    proxy_request_buffering off;
+    proxy_pass http://api:8080/briefs/;
+    proxy_set_header Host $host;
+    proxy_set_header X-Real-IP $remote_addr;
+    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
+    proxy_set_header X-Forwarded-Proto $scheme;
+    proxy_read_timeout 300s;
+    proxy_connect_timeout 60s;
+  }
```

## File: apps/miniapp_api/main.py

```diff
--- a/apps/miniapp_api/main.py
+++ b/apps/miniapp_api/main.py
@@
 try:
     from apps.miniapp_api.routers.public_tasks import router as public_tasks_router
     app.include_router(public_tasks_router, prefix="/api")
 except Exception as e:
     logging.getLogger(__name__).warning("Failed to include public_tasks router: %s", e.__class__.__name__)
 
+try:
+    from apps.miniapp_api.routers import briefs as briefs_router
+
+    app.include_router(briefs_router.router)
+    if hasattr(briefs_router, "alias_router"):
+        app.include_router(briefs_router.alias_router)
+except Exception as e:
+    logging.getLogger(__name__).warning("Failed to include briefs router: %s", e.__class__.__name__)
+
 
 @app.get("/healthz")
 async def healthz() -> dict:
     return {"ok": True}
```

## File: apps/miniapp_api/routers/briefs.py

```diff
--- /dev/null
+++ b/apps/miniapp_api/routers/briefs.py
@@
+"""Brief upload endpoints with idempotency and integrations."""
+from __future__ import annotations
+
+import hashlib
+import logging
+import os
+import pathlib
+import re
+from typing import Optional
+
+from fastapi import APIRouter, File, Form, HTTPException, UploadFile
+from fastapi.responses import JSONResponse
+from pydantic import EmailStr
+
+from apps.miniapp_api.services.notion import create_brief_page
+from apps.miniapp_api.services.telegram import build_caption, send_brief
+from apps.miniapp_api.utils.idempotency import reserve_fp
+
+router = APIRouter(prefix="/briefs", tags=["briefs"])
+alias_router = APIRouter(tags=["briefs-alias"])
```

```diff
@@
+    is_new, reserved_request_id = await reserve_fp(fingerprint, request_id)
+
+    if not is_new:
+        logger.info("Duplicate brief submission detected: %s", reserved_request_id)
+        return JSONResponse({"ok": True, "request_id": reserved_request_id, "notion_page_id": None, "dedup": True})
+
+    safe_filename = _sanitize_name(file.filename or "file")
+    upload_dir = pathlib.Path(UPLOAD_BASE_DIR) / reserved_request_id
+    upload_dir.mkdir(parents=True, exist_ok=True)
+    file_path = upload_dir / safe_filename
+    file_path.write_bytes(file_bytes)
```

```diff
@@
+@alias_router.post("/api/briefs/upload")
+async def upload_brief_alias(...):
+    return await _upload_brief_handler(
+        file=file,
+        locale=locale,
+        name=name,
+        company=company,
+        phone=phone,
+        email=email,
+        message=message,
+        request_id=request_id,
+    )
```

## File: apps/miniapp_api/services/notion.py

```diff
--- /dev/null
+++ b/apps/miniapp_api/services/notion.py
@@
+"""Notion helpers for brief uploads."""
+from __future__ import annotations
+
+import asyncio
+import logging
+from typing import Optional
+
+from notion_client import APIResponseError, Client
```

## File: apps/miniapp_api/services/telegram.py

```diff
--- /dev/null
+++ b/apps/miniapp_api/services/telegram.py
@@
+"""Telegram service helpers for miniapp brief uploads."""
+from __future__ import annotations
+
+import logging
+import os
+
+import httpx
```

## File: apps/miniapp_api/utils/idempotency.py

```diff
--- /dev/null
+++ b/apps/miniapp_api/utils/idempotency.py
@@
+"""Idempotency utilities for brief uploads."""
+from __future__ import annotations
+
+import asyncio
+import logging
+import os
+from datetime import datetime
+from typing import Optional, Tuple
+
+from redis import Redis
+from ulid import ULID
```

## File: apps/miniapp-api/requirements.txt

```diff
--- a/apps/miniapp-api/requirements.txt
+++ b/apps/miniapp-api/requirements.txt
@@
-notion-client==2.2.1
-httpx==0.27.2
+notion-client==2.2.1
+httpx==0.27.2
+redis>=5.0.0
+ulid-py>=1.1.0
```

## File: infra/compose/miniapp.localbuild.override.yml

```diff
--- a/infra/compose/miniapp.localbuild.override.yml
+++ b/infra/compose/miniapp.localbuild.override.yml
@@
 services:
   api:
     build:
-      context: ../../apps/api
+      context: ../../apps/miniapp-api
       dockerfile: Dockerfile
     image: local/miniapp-api:dev
```

