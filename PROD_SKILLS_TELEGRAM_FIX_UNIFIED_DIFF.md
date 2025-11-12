# Production Skills & Telegram Export Fix - Unified Diff

## Summary
Fixed route shadowing for `/api/skills/debug` by reordering routes in the skills router.

## Changes

### 1. Skills Router: Route Reordering

**File:** `apps/miniapp-api/routers/skills.py`

Moved `/api/skills/debug` route before `/api/skills/{slug}` to prevent shadowing.

```diff
--- a/apps/miniapp-api/routers/skills.py
+++ b/apps/miniapp-api/routers/skills.py
@@ -140,6 +140,35 @@ def list_skills_api(
     return _list_skills_impl(request=request, lang=lang)
 
 
+@api_router.get("/skills/debug")
+def debug_skills(request: Request) -> Dict[str, Any]:
+    """Minimal diagnostics for skills provider without leaking secrets."""
+    repo = _repo(request)
+    snap = repo.snapshot()
+    csv_path_env = os.getenv("SKILLS_CSV_PATH")
+    if csv_path_env:
+        csv_path = Path(csv_path_env)
+    else:
+        csv_path = getattr(repo, "_csv_path", Path("/app/data/skills.csv"))
+    notion_token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")
+    notion_db = os.getenv("NOTION_DB_SKILLS") or os.getenv("NOTION_DB")
+    sample = []
+    for s in (snap.skills[:2] if getattr(snap, "skills", None) else []):
+        sample.append({"slug": getattr(s, "key", ""), "title_en": s.title_en[:60], "title_ru": s.title_ru[:60]})
+    return {
+        "provider": getattr(snap, "source", None) or "unknown",
+        "csv_path": str(csv_path),
+        "csv_exists": csv_path.exists(),
+        "notion": {
+            "token": "SET" if notion_token else "EMPTY",
+            "db": "SET" if notion_db else "EMPTY",
+            "ok": bool(getattr(snap, "notion", False)),
+        },
+        "count": len(getattr(snap, "skills", []) or []),
+        "sample": sample,
+    }
+
+
 @api_router.get("/skills/{slug}")
 def get_skill_api(
     slug: str,
@@ -174,32 +203,3 @@ def search_skills_api(
     ]
 
 
-@api_router.get("/skills/debug")
-def debug_skills(request: Request) -> Dict[str, Any]:
-    """Minimal diagnostics for skills provider without leaking secrets."""
-    repo = _repo(request)
-    snap = repo.snapshot()
-    csv_path_env = os.getenv("SKILLS_CSV_PATH")
-    if csv_path_env:
-        csv_path = Path(csv_path_env)
-    else:
-        csv_path = getattr(repo, "_csv_path", Path("/app/data/skills.csv"))
-    notion_token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")
-    notion_db = os.getenv("NOTION_DB_SKILLS") or os.getenv("NOTION_DB")
-    sample = []
-    for s in (snap.skills[:2] if getattr(snap, "skills", None) else []):
-        sample.append({"slug": getattr(s, "key", ""), "title_en": s.title_en[:60], "title_ru": s.title_ru[:60]})
-    return {
-        "provider": getattr(snap, "source", None) or "unknown",
-        "csv_path": str(csv_path),
-        "csv_exists": csv_path.exists(),
-        "notion": {
-            "token": "SET" if notion_token else "EMPTY",
-            "db": "SET" if notion_db else "EMPTY",
-            "ok": bool(getattr(snap, "notion", False)),
-        },
-        "count": len(getattr(snap, "skills", []) or []),
-        "sample": sample,
-    }
-
-
```

## Notes

### Already Present (No Changes Needed)

1. **Telegram Selftest Route**: Already exists at `/api/telegram/selftest` in `apps/miniapp-api/routers/chat_v2.py` (line 133) and is wired via `chat_router` in `main.py` (line 94).

2. **Compose Environment Variables**: All required env vars are already present in `infra/compose/miniapp.compose.yaml`:
   - `SKILLS_SOURCE` (line 20)
   - `SKILLS_CSV_PATH` (line 21)
   - `TELEGRAM_TOKEN` (line 26)
   - `TELEGRAM_BOT_TOKEN` (line 27)
   - `ADMIN_CHAT_ID` (line 28)
   - `TELEGRAM_ADMIN_CHAT_ID` (line 29)

3. **Export Handler**: Already handles both `{items:[...]}` and `{messages:[...]}` payloads (line 167-168 in `chat_v2.py`) and has proper error handling with 400 for validation errors and 502 for network/API errors.

