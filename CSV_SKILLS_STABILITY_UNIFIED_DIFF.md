# CSV Skills Mode Stability - Unified Diff

## File: apps/miniapp-api/app/services/skills_loader.py

```diff
--- a/apps/miniapp-api/app/services/skills_loader.py
+++ b/apps/miniapp-api/app/services/skills_loader.py
@@ -19,16 +19,16 @@ logger = logging.getLogger(__name__)
 # CSV header aliases for tolerant ingestion
 # Supports exact headers: Title EN, Bullets EN, Bullets RU, Examples EN, Examples RU, Short EN, Short RU, Slug, Tags, Title RU
 CSV_ALIASES = {
-    "key": ["key", "slug", "id", "slug", "Slug"],
-    "title_en": ["title_en", "name_en", "en_title", "en_name", "title", "title en", "Title EN", "Title"],
-    "title_ru": ["title_ru", "name_ru", "ru_title", "ru_name", "title ru", "Title RU"],
-    "short_en": ["short_en", "summary_en", "en_short", "en_summary", "short en", "Short EN"],
-    "short_ru": ["short_ru", "summary_ru", "ru_short", "ru_summary", "short ru", "Short RU"],
-    "tags": ["tags", "labels", "categories", "Tags"],
-    "bullets_en": ["bullets_en", "points_en", "en_bullets", "bullets en", "Bullets EN"],
-    "bullets_ru": ["bullets_ru", "points_ru", "ru_bullets", "bullets ru", "Bullets RU"],
-    "examples_en": ["examples_en", "cases_en", "en_examples", "example_en", "examples en", "Examples EN"],
-    "examples_ru": ["examples_ru", "cases_ru", "ru_examples", "example_ru", "examples ru", "Examples RU"],
+    "key": ["slug", "key", "id"],
+    "title_en": ["title en", "title_en", "name_en", "en_title", "en_name", "title"],
+    "title_ru": ["title ru", "title_ru", "name_ru", "ru_title", "ru_name"],
+    "short_en": ["short en", "short_en", "summary_en", "en_short", "en_summary"],
+    "short_ru": ["short ru", "short_ru", "summary_ru", "ru_short", "ru_summary"],
+    "tags": ["tags", "labels", "categories"],
+    "bullets_en": ["bullets en", "bullets_en", "points_en", "en_bullets"],
+    "bullets_ru": ["bullets ru", "bullets_ru", "points_ru", "ru_bullets"],
+    "examples_en": ["examples en", "examples_en", "cases_en", "en_examples", "example_en"],
+    "examples_ru": ["examples ru", "examples_ru", "cases_ru", "ru_examples", "example_ru"],
     "weight": ["weight", "order", "prio", "rank"],
     "pinned": ["pinned", "pin", "featured"],
 }
@@ -244,11 +244,13 @@ class SkillsLoader:
             for i, row in enumerate(normalized_rows):
                 # Convert all values to strings, handling NaN and None
                 row_str = {}
                 for k, v in row.items():
-                    key_lower = str(k).lower()
+                    key_lower = str(k).lower().strip()
+                    # Handle NaN/None/empty: convert to empty string
                     if pd.isna(v) or v is None:
                         row_str[key_lower] = ""
                     else:
-                        row_str[key_lower] = str(v)
+                        # Convert to string and strip
+                        row_str[key_lower] = str(v).strip()
 
                 key = _h(row_str, "key") or f"skill_{i}"
                 title_en = _h(row_str, "title_en") or key
@@ -267,6 +269,8 @@ class SkillsLoader:
                 weight = _to_int(_h(row_str, "weight"), 0)
                 pinned = _to_bool(_h(row_str, "pinned"))
 
+                # Skip rows without at least one title
                 if not (title_en or title_ru):
+                    logger.debug("Skipping row %d: no title_en or title_ru", i)
                     continue
```

## File: apps/miniapp-api/routers/skills.py

```diff
--- a/apps/miniapp-api/routers/skills.py
+++ b/apps/miniapp-api/routers/skills.py
@@ -56,12 +56,19 @@ def _project_detail(skill: SkillRecord, lang: str) -> Dict[str, Any]:
 
 
 def _load_skills_with_fallback() -> List[SkillRecord]:
-    """Load skills from CSV with fallback to hardcoded skills if CSV fails."""
+    """Load skills from CSV with fallback to hardcoded skills if CSV fails.
+    When SKILLS_SOURCE=csv, NEVER calls Notion - only CSV or fallback."""
     source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
     if source == "csv":
-        skills = get_loader().load_skills()
-        if not skills:
+        try:
+            skills = get_loader().load_skills()
+            if not skills or len(skills) == 0:
+                logger.warning("CSV loader returned 0 skills, using fallback")
+                return get_fallback_skills()
+            return skills
+        except Exception as exc:
+            logger.error("CSV loader failed, using fallback: %s", exc, exc_info=True)
             return get_fallback_skills()
-        return skills
     # For non-CSV mode, use repository (which may use Notion or CSV)
     return []
 
@@ -69,12 +76,20 @@ def _load_skills_with_fallback() -> List[SkillRecord]:
 def _list_skills_impl(request: Request, lang: Optional[str]) -> List[Dict[str, Any]]:
     source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
     if source == "csv":
+        # CSV mode: never call Notion, always use CSV loader with fallback
         skills = _load_skills_with_fallback()
     else:
+        # Non-CSV mode: use repository (may use Notion or CSV)
         repo = _repo(request)
         snapshot = repo.snapshot()
         skills = snapshot.skills
+    # Ensure we never return empty list - fallback should have been applied in CSV mode
     if not skills:
+        logger.warning("_list_skills_impl: skills list is empty after loading")
+        if source == "csv":
+            # Last resort fallback
+            skills = get_fallback_skills()
+        else:
             return []
     lang_key = _lang_key(lang)
     if lang:
@@ -99,8 +114,10 @@ def _list_skills_impl(request: Request, lang: Optional[str]) -> List[Dict[str,
 def _get_skill_impl(
     slug: str,
     request: Request,
     lang: Optional[str],
 ) -> Dict[str, Any]:
     source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
     if source == "csv":
+        # CSV mode: never call Notion, always use CSV loader with fallback
         skills = _load_skills_with_fallback()
         skill = next((s for s in skills if s.key == slug), None)
     else:
+        # Non-CSV mode: use repository (may use Notion or CSV)
         repo = _repo(request)
         snapshot = repo.snapshot()
         skill = next((item for item in snapshot.skills if item.key == slug), None)
@@ -172,7 +189,8 @@ def get_skill_api(
 @api_router.get("/skills/debug")
 def debug_skills(request: Request) -> Dict[str, Any]:
-    """Minimal diagnostics for skills provider without leaking secrets."""
+    """Detailed diagnostics for skills provider without leaking secrets.
+    When SKILLS_SOURCE=csv, ensures no Notion calls are made."""
     source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
     csv_path_env = os.getenv("SKILLS_CSV_PATH")
     if csv_path_env:
@@ -182,6 +200,7 @@ def debug_skills(request: Request) -> Dict[str, Any]:
     
     errors: List[str] = []
     csv_ok = False
+    csv_exists = csv_path.exists()
     
     if source == "csv":
+        # CSV mode: NEVER call Notion
         # Try to load CSV directly to check if it works
         try:
             loader = get_loader()
@@ -195,6 +214,7 @@ def debug_skills(request: Request) -> Dict[str, Any]:
         return {
             "source": actual_source,
             "count": len(skills),
             "csv_path": str(csv_path),
+            "csv_exists": csv_exists,
             "csv_ok": csv_ok,
             "errors": errors if errors else None,
             "sample": sample,
@@ -202,6 +222,7 @@ def debug_skills(request: Request) -> Dict[str, Any]:
     else:
+        # Non-CSV mode: may use Notion
         repo = _repo(request)
         snap = repo.snapshot()
         notion_token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")
@@ -218,6 +239,7 @@ def debug_skills(request: Request) -> Dict[str, Any]:
             "count": len(getattr(snap, "skills", []) or []),
             "csv_path": str(csv_path),
+            "csv_exists": csv_exists,
             "csv_ok": csv_ok,
             "errors": errors if errors else None,
             "notion": {
@@ -235,6 +257,7 @@ def search_skills_api(
 ) -> List[Dict[str, Any]]:
     source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
     if source == "csv":
+        # CSV mode: never call Notion, always use CSV loader with fallback
         skills = _load_skills_with_fallback()
         # Simple search using loader
         from ..services.skills_loader import get_loader
@@ -242,6 +265,7 @@ def search_skills_api(
         top_skills = get_loader().search_skills(q, lang=lang_key, top_k=limit)
     else:
+        # Non-CSV mode: use repository (may use Notion or CSV)
         repo = _repo(request)
         lang_key = _lang_key(lang) if lang else "en"
         top_skills = repo.relevant_skills(q, top_k=limit)
@@ -342,6 +366,7 @@ def ask_skills(request: Request, body: AskRequest) -> AskResponse:
     # Load skills using the loader with fallback
     if source == "csv":
+        # CSV mode: never call Notion, always use CSV loader with fallback
         skills = _load_skills_with_fallback()
     else:
+        # Non-CSV mode: try loader first, then fallback
         loader = get_loader()
         skills = loader.load_skills()
         if not skills:
@@ -365,10 +390,12 @@ def ask_skills(request: Request, body: AskRequest) -> AskResponse:
         selected_skills = [s for s in skills if s.key in body.selected]
         if not selected_skills:
             # Fallback to search if selected not found
             if source == "csv":
+                # CSV mode: never call Notion
                 from ..services.skills_loader import get_loader
                 selected_skills = get_loader().search_skills(query, lang=lang_key, top_k=5)
             else:
+                # Non-CSV mode: use repository (may use Notion)
                 repo = _repo(request)
                 selected_skills = repo.relevant_skills(query, top_k=5)
     else:
         if source == "csv":
+            # CSV mode: never call Notion
             from ..services.skills_loader import get_loader
             selected_skills = get_loader().search_skills(query, lang=lang_key, top_k=5)
         else:
+            # Non-CSV mode: use repository (may use Notion)
             repo = _repo(request)
             selected_skills = repo.relevant_skills(query, top_k=5)
```

## File: apps/miniapp-web/src/pages/SkillsPage.tsx

```diff
--- a/apps/miniapp-web/src/pages/SkillsPage.tsx
+++ b/apps/miniapp-web/src/pages/SkillsPage.tsx
@@ -199,7 +199,7 @@ export function SkillsPage({ lang, selectedSlug, onBack, onSelect, onCloseDeta
     // Only show "NoSkills" when status is success and list is empty (200 + [])
     if (status === "success" && skills.length === 0) {
       return (
         <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
-          {lang === 'ru' ? 'Пока нет навыков для отображения.' : 'No skills are published yet.'}
+          {lang === 'ru' ? 'Пока нет навыков для отображения.' : 'No skills available yet.'}
         </div>
       )
     }
```

