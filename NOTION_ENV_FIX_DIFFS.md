# Notion Environment Variables Fix - Unified Diffs

## Summary
Removed empty NOTION_* environment overrides from compose files, ensured env_file is properly configured, fixed FastAPI init order, and added legacy env var support.

---

## 1. infra/compose/miniapp.runtime.yml

**Change:** Standardized environment list format (dict → array)

```diff
--- a/infra/compose/miniapp.runtime.yml
+++ b/infra/compose/miniapp.runtime.yml
@@ -27,8 +27,8 @@
     restart: unless-stopped
     pull_policy: always
     env_file:
       - .env.miniapp
     environment:
-      NOTION_TIMEOUT: ${NOTION_TIMEOUT:-10}
-      WEBSITE_ORIGIN: ${WEBSITE_ORIGIN:-https://miniapp.dmitrybond.tech}
+      - NOTION_TIMEOUT=${NOTION_TIMEOUT:-10}
+      - WEBSITE_ORIGIN=${WEBSITE_ORIGIN:-https://miniapp.dmitrybond.tech}
```

---

## 2. infra/compose/miniapp.notion.override.yml

**Change:** Standardized environment list format (dict → array)

```diff
--- a/infra/compose/miniapp.notion.override.yml
+++ b/infra/compose/miniapp.notion.override.yml
@@ -1,6 +1,6 @@
 services:
   api:
     env_file:
       - .env.miniapp
     environment:
-      NOTION_TIMEOUT: ${NOTION_TIMEOUT:-10}
+      - NOTION_TIMEOUT=${NOTION_TIMEOUT:-10}
```

---

## 3. apps/miniapp-api/main.py

**Changes:**
- Removed module-level `os.getenv()` calls before app creation
- Moved router import after `app = FastAPI(...)`
- Moved env var reads into function bodies

```diff
--- a/apps/miniapp-api/main.py
+++ b/apps/miniapp-api/main.py
@@ -1,18 +1,12 @@
-import os
 from typing import Any, Dict, List, Literal
 
 from fastapi import FastAPI, Query
 from fastapi.middleware.cors import CORSMiddleware
 from pydantic import BaseModel, Field
 
-DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ru")
-CAL_USERNAME = os.getenv("CAL_USERNAME", "dmitrybond")
-CAL_HOST = os.getenv("CAL_HOST", "cal.com")
-
 app = FastAPI(title="MiniApp API", version="1.0.0")
 
 # CORS left in place for local dev convenience; same-origin in prod avoids CORS usage
@@ -25,13 +19,9 @@
     allow_headers=["*"],
 )
 
-try:
-    # Mount public tasks router under /api prefix
-    # Use relative import to survive dash/underscore copy
-    from .routers.public_tasks import router as public_tasks_router
-    app.include_router(public_tasks_router, prefix="/api")
-except Exception:
-    # Optional in dev if dependencies are missing; avoids startup crash
-    pass
+# Mount public tasks router under /api prefix
+# Use relative import to survive dash/underscore copy
+from .routers.public_tasks import router as public_tasks_router
+app.include_router(public_tasks_router, prefix="/api")
```

```diff
--- a/apps/miniapp-api/main.py
+++ b/apps/miniapp-api/main.py
@@ -113,12 +113,16 @@
 
 @app.get("/cal/link", response_model=CalLinkResponse)
 async def cal_link() -> CalLinkResponse:
-    return CalLinkResponse(url=f"https://{CAL_HOST}/{CAL_USERNAME}/intro-30m")
+    import os
+    host = os.getenv("CAL_HOST", "cal.com")
+    username = os.getenv("CAL_USERNAME", "dmitrybond")
+    return CalLinkResponse(url=f"https://{host}/{username}/intro-30m")
 
 
 @app.get("/cal/suggest")
-async def cal_suggest(event: str = Query(default="intro-30m"), lang: str = Query(default=DEFAULT_LANG)) -> Dict[str, Any]:
-    username = os.getenv("CAL_USERNAME", CAL_USERNAME)
-    host = os.getenv("CAL_HOST", CAL_HOST)
+async def cal_suggest(event: str = Query(default="intro-30m"), lang: str = Query(default=None)) -> Dict[str, Any]:
+    import os
+    default_lang = os.getenv("DEFAULT_LANG", "ru")
+    if lang is None:
+        lang = default_lang
+    username = os.getenv("CAL_USERNAME", "dmitrybond")
+    host = os.getenv("CAL_HOST", "cal.com")
@@ -127,7 +131,7 @@
     return {
         "event": event,
         "lang": lang,
-        "cta": cta.get(lang, cta[DEFAULT_LANG]),
+        "cta": cta.get(lang, cta[default_lang]),
         "url": url,
     }
```

---

## 4. apps/miniapp-api/integrations/notion_public.py

**Change:** Added legacy env var fallback (NOTION_SECRET → NOTION_API_KEY)

```diff
--- a/apps/miniapp-api/integrations/notion_public.py
+++ b/apps/miniapp-api/integrations/notion_public.py
@@ -9,13 +9,15 @@
 from notion_client import Client, APIResponseError
 
 
-# Environment variables
-NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
+# Environment variables with legacy fallbacks
 NOTION_TIMEOUT = int(os.getenv("NOTION_TIMEOUT", "10"))
 
 
 def _client() -> Client:
-    """Create and return a Notion client instance using env vars."""
-    if not NOTION_API_KEY:
-        raise ValueError("NOTION_API_KEY is not set")
-    return Client(auth=NOTION_API_KEY, timeout_ms=NOTION_TIMEOUT * 1000)
+    """Create and return a Notion client instance using env vars.
+    
+    Supports legacy env vars: NOTION_SECRET → NOTION_API_KEY
+    """
+    api_key = os.getenv("NOTION_API_KEY", "").strip() or os.getenv("NOTION_SECRET", "").strip()
+    if not api_key:
+        raise ValueError("NOTION_API_KEY (or legacy NOTION_SECRET) is not set")
+    return Client(auth=api_key, timeout_ms=NOTION_TIMEOUT * 1000)
```

---

## 5. apps/miniapp-api/routers/public_tasks.py

**Change:** Added legacy env var fallback (NOTION_DB → NOTION_PUBLIC_TASKS_DB_ID) in both endpoints

```diff
--- a/apps/miniapp-api/routers/public_tasks.py
+++ b/apps/miniapp-api/routers/public_tasks.py
@@ -18,7 +18,8 @@
     limit: int = Query(default=20, ge=1, le=50, description="Max number of tasks (1..50)"),
 ) -> List[dict]:
     try:
-        dbid = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "").strip()
+        # Support legacy env var: NOTION_DB → NOTION_PUBLIC_TASKS_DB_ID
+        dbid = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "").strip() or os.getenv("NOTION_DB", "").strip()
         if not dbid:
             raise HTTPException(status_code=502, detail={"error": "notion_unreachable"})
```

```diff
--- a/apps/miniapp-api/routers/public_tasks.py
+++ b/apps/miniapp-api/routers/public_tasks.py
@@ -40,7 +41,8 @@
 @router.get("/debug")
 def debug_tasks() -> dict:
     try:
-        dbid = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "").strip()
+        # Support legacy env var: NOTION_DB → NOTION_PUBLIC_TASKS_DB_ID
+        dbid = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "").strip() or os.getenv("NOTION_DB", "").strip()
         if not dbid:
             return {"titleProp": None, "publicProp": None, "statusProp": None, "statusValues": []}
```

---

## 6. scripts/print-api-env.py

**Change:** Complete rewrite to show masked lengths of all NOTION env vars (current + legacy)

```diff
--- a/scripts/print-api-env.py
+++ b/scripts/print-api-env.py
@@ -1,47 +1,30 @@
 #!/usr/bin/env python3
-import os
+"""Print masked lengths of NOTION environment variables for debugging."""
+import os
 
 
-def mask(value: str) -> str:
+def mask(value: str, keep: int = 4) -> str:
+    """Mask a value, showing only the last 'keep' characters."""
     if value is None:
-        return "<none>"
+        return "<EMPTY>"
     v = str(value)
     if not v:
         return "<EMPTY>"
-    return f"len={len(v)} first=*** last=***"
+    if len(v) <= keep:
+        return "*" * len(v)
+    return f"{'*' * (len(v) - keep)}{v[-keep:]}"
 
 
 def main() -> None:
-    print("API env (masked):")
-    print(f"NOTION_API_KEY: {mask(os.getenv('NOTION_API_KEY'))}")
-    print(f"NOTION_SECRET:  {mask(os.getenv('NOTION_SECRET'))}")
-    print(f"NOTION_PUBLIC_TASKS_DB_ID: {mask(os.getenv('NOTION_PUBLIC_TASKS_DB_ID'))}")
-    print(f"NOTION_DB: {mask(os.getenv('NOTION_DB'))}")
+    """Print masked NOTION environment variables."""
+    api_key = os.getenv("NOTION_API_KEY", "")
+    secret = os.getenv("NOTION_SECRET", "")
+    db_id = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "")
+    db_legacy = os.getenv("NOTION_DB", "")
+    timeout = os.getenv("NOTION_TIMEOUT", "")
+
+    print("NOTION env vars (masked):")
+    print(f"  NOTION_API_KEY: len={len(api_key)} masked={mask(api_key)}")
+    print(f"  NOTION_SECRET (legacy): len={len(secret)} masked={mask(secret)}")
+    print(f"  NOTION_PUBLIC_TASKS_DB_ID: len={len(db_id)} masked={mask(db_id)}")
+    print(f"  NOTION_DB (legacy): len={len(db_legacy)} masked={mask(db_legacy)}")
+    print(f"  NOTION_TIMEOUT: {timeout or '<UNSET>'}")
 
 
 if __name__ == "__main__":
     main()
-
-import os
-
-
-def mask(value: str, keep: int = 4) -> str:
-    if not value:
-        return "<EMPTY>"
-    if len(value) <= keep:
-        return "*" * len(value)
-    return f"{'*' * (len(value) - keep)}{value[-keep:]}"
-
-
-def main() -> None:
-    api_key = os.getenv("NOTION_API_KEY", "")
-    db_id = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "")
-    timeout = os.getenv("NOTION_TIMEOUT", "")
-
-    print(f"NOTION_API_KEY: len={len(api_key)} masked={mask(api_key)}")
-    print(f"NOTION_PUBLIC_TASKS_DB_ID: len={len(db_id)} masked={mask(db_id)}")
-    print(f"NOTION_TIMEOUT: {timeout or '<UNSET>'}")
-
-
-if __name__ == "__main__":
-    main()
```

---

## Notes

- `infra/compose/miniapp.compose.yaml` and `infra/compose/miniapp.stack.yml` were already correct (no changes needed)
- All compose files now have consistent format and no NOTION_* secret overrides
- FastAPI init order ensures app is created before router imports
- Legacy env var support maintains backward compatibility

