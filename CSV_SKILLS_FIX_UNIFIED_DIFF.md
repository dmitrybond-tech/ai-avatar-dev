# CSV Skills Fix - Unified Diff

## File: infra/compose/miniapp.csv.override.yml

```diff
--- a/infra/compose/miniapp.csv.override.yml
+++ b/infra/compose/miniapp.csv.override.yml
@@ -1,9 +1,9 @@
 # Optional override for mounting host CSV file and forcing CSV source
-# Usage: docker compose -f miniapp.compose.yaml -f miniapp.csv.override.yml up
+# Usage: docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml up
 services:
   api:
     environment:
-      SKILLS_SOURCE: csv
-      SKILLS_CSV_PATH: /app/data/skills.csv
+      SKILLS_SOURCE: ${SKILLS_SOURCE:-csv}
+      SKILLS_CSV_PATH: ${SKILLS_CSV_PATH:-/app/data/skills.csv}
     volumes:
-      - ../../apps/miniapp-api/data/skills.csv:/app/data/skills.csv:ro
+      - ../../apps/miniapp-api/data:/app/data:ro
```

## File: apps/miniapp-api/app/services/skills_loader.py

```diff
--- a/apps/miniapp-api/app/services/skills_loader.py
+++ b/apps/miniapp-api/app/services/skills_loader.py
@@ -9,6 +9,7 @@ from pathlib import Path
 from threading import Lock
 from typing import Dict, List, Optional
 
+import pandas as pd
 from rapidfuzz import process
 
 from ..core import env as env_utils
@@ -187,54 +188,69 @@ class SkillsLoader:
             return None
 
     def _load_csv(self) -> List[SkillRecord]:
-        """Load skills from CSV with UTF-8 BOM handling and robust parsing."""
+        """Load skills from CSV with UTF-8 BOM handling and robust parsing using pandas."""
         csv_path = self._csv_path
         if not csv_path.exists():
             logger.warning("Skills CSV path %s does not exist", csv_path)
             return []
 
         items: List[SkillRecord] = []
+        encoding_used = None
         try:
             # Try UTF-8 with BOM first, then fallback to UTF-8
             encodings = ["utf-8-sig", "utf-8"]
-            content = None
-            encoding_used = None
+            df = None
 
             for enc in encodings:
                 try:
-                    with csv_path.open(encoding=enc, newline="") as f:
-                        content = f.read()
-                        encoding_used = enc
-                        break
+                    # Use pandas with python engine for robust handling of quoted multiline cells
+                    # on_bad_lines parameter available in pandas >= 1.3.0
+                    read_kwargs = {
+                        "encoding": enc,
+                        "engine": "python",
+                        "quotechar": '"',
+                        "skipinitialspace": True,
+                    }
+                    # Try with on_bad_lines for newer pandas, fallback to error_bad_lines for older
+                    try:
+                        df = pd.read_csv(csv_path, **read_kwargs, on_bad_lines="skip")
+                    except TypeError:
+                        # Fallback for older pandas versions
+                        df = pd.read_csv(csv_path, **read_kwargs, error_bad_lines=False, warn_bad_lines=False)
+                    encoding_used = enc
+                    break
                 except UnicodeDecodeError:
                     continue
+                except Exception as exc:
+                    logger.warning("Failed to read CSV %s with encoding %s: %s", csv_path, enc, exc)
+                    continue
 
-            if content is None:
-                logger.error("Failed to decode CSV %s with any encoding", csv_path)
+            if df is None or df.empty:
+                logger.error("Failed to decode CSV %s with any encoding or CSV is empty", csv_path)
                 return []
 
-            # Parse CSV content
-            import io
+            # Normalize column names to lowercase for case-insensitive matching
+            df.columns = df.columns.str.lower().str.strip()
 
-            reader = csv.DictReader(io.StringIO(content))
-            normalized_rows = []
-            for row in reader:
-                normalized = {str(k).lower(): v for k, v in row.items()}
-                normalized_rows.append(normalized)
+            # Convert DataFrame to list of dicts
+            normalized_rows = df.to_dict("records")
 
             for i, row in enumerate(normalized_rows):
-                key = _h(row, "key") or f"skill_{i}"
-                title_en = _h(row, "title_en") or key
-                title_ru = _h(row, "title_ru") or title_en
-                short_en = _h(row, "short_en")
-                short_ru = _h(row, "short_ru") or short_en
-                tags = _split_list(_h(row, "tags"))
-                bullets_en = _split_lines(_h(row, "bullets_en"))
-                bullets_ru = _split_lines(_h(row, "bullets_ru"))
-                examples_en = _split_lines(_h(row, "examples_en"))
-                examples_ru = _split_lines(_h(row, "examples_ru"))
-                weight = _to_int(_h(row, "weight"), 0)
-                pinned = _to_bool(_h(row, "pinned"))
+                # Convert all values to strings, handling NaN
+                row_str = {str(k).lower(): (str(v) if pd.notna(v) else "") for k, v in row.items()}
+
+                key = _h(row_str, "key") or f"skill_{i}"
+                title_en = _h(row_str, "title_en") or key
+                title_ru = _h(row_str, "title_ru") or title_en
+                short_en = _h(row_str, "short_en")
+                short_ru = _h(row_str, "short_ru") or short_en
+                tags = _split_list(_h(row_str, "tags"))
+                bullets_en = _split_lines(_h(row_str, "bullets_en"))
+                bullets_ru = _split_lines(_h(row_str, "bullets_ru"))
+                examples_en = _split_lines(_h(row_str, "examples_en"))
+                examples_ru = _split_lines(_h(row_str, "examples_ru"))
+                weight = _to_int(_h(row_str, "weight"), 0)
+                pinned = _to_bool(_h(row_str, "pinned"))
 
                 if not (title_en or title_ru):
                     continue
@@ -256,7 +272,7 @@ class SkillsLoader:
                     )
                 )
         except Exception as exc:
-            logger.error("Failed to read CSV %s: %s", csv_path, exc, exc_info=True)
+            logger.error("skills_csv_read_failed: Failed to read CSV %s: %s", csv_path, exc, exc_info=True)
             return []
 
         # Stable ordering: pinned desc, weight desc, key asc
```

## File: apps/miniapp-api/routers/skills.py

```diff
--- a/apps/miniapp-api/routers/skills.py
+++ b/apps/miniapp-api/routers/skills.py
@@ -179,20 +179,39 @@ def debug_skills(request: Request) -> Dict[str, Any]:
     else:
         csv_path = Path("/app/data/skills.csv")
     
+    errors: List[str] = []
+    csv_ok = False
+    
     if source == "csv":
+        # Try to load CSV directly to check if it works
+        try:
+            loader = get_loader()
+            csv_skills = loader.load_skills()
+            csv_ok = len(csv_skills) > 0
+            if not csv_ok:
+                errors.append("CSV loaded but returned 0 skills")
+        except Exception as exc:
+            errors.append(f"CSV load failed: {str(exc)[:200]}")
+            csv_ok = False
+        
+        # Load with fallback
         skills = _load_skills_with_fallback()
-        actual_source = "fallback" if len(get_loader().load_skills()) == 0 else "csv"
+        actual_source = "fallback" if not csv_ok else "csv"
+        
         sample = []
         for s in skills[:2]:
             sample.append({
                 "slug": s.key,
                 "title": s.title("en")[:60],
             })
+        
         return {
             "source": actual_source,
             "count": len(skills),
             "csv_path": str(csv_path),
             "csv_exists": csv_path.exists(),
+            "csv_ok": csv_ok,
+            "errors": errors if errors else None,
             "sample": sample,
         }
     else:
@@ -200,14 +219,27 @@ def debug_skills(request: Request) -> Dict[str, Any]:
         snap = repo.snapshot()
         notion_token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")
         notion_db = os.getenv("NOTION_DB_SKILLS") or os.getenv("NOTION_DB")
+        
+        # Check CSV status even in non-CSV mode
+        try:
+            loader = get_loader()
+            csv_skills = loader.load_skills()
+            csv_ok = len(csv_skills) > 0
+        except Exception as exc:
+            errors.append(f"CSV check failed: {str(exc)[:200]}")
+            csv_ok = False
+        
         sample = []
         for s in (snap.skills[:2] if getattr(snap, "skills", None) else []):
             sample.append({"slug": getattr(s, "key", ""), "title_en": s.title_en[:60], "title_ru": s.title_ru[:60]})
+        
         return {
             "source": getattr(snap, "source", None) or "unknown",
             "count": len(getattr(snap, "skills", []) or []),
             "csv_path": str(csv_path),
             "csv_exists": csv_path.exists(),
+            "csv_ok": csv_ok,
+            "errors": errors if errors else None,
             "notion": {
                 "token": "SET" if notion_token else "EMPTY",
                 "db": "SET" if notion_db else "EMPTY",
```

