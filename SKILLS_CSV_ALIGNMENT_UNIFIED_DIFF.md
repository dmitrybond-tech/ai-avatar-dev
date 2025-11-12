# Skills CSV Alignment - Unified Diff

## File: apps/miniapp-api/app/services/skills_loader.py

```diff
--- a/apps/miniapp-api/app/services/skills_loader.py
+++ b/apps/miniapp-api/app/services/skills_loader.py
@@ -17,15 +17,15 @@ logger = logging.getLogger(__name__)
 # CSV header aliases for tolerant ingestion
 CSV_ALIASES = {
     "key": ["key", "slug", "id"],
-    "title_en": ["title_en", "name_en", "en_title", "en_name", "title"],
-    "title_ru": ["title_ru", "name_ru", "ru_title", "ru_name"],
-    "short_en": ["short_en", "summary_en", "en_short", "en_summary"],
-    "short_ru": ["short_ru", "summary_ru", "ru_short", "ru_summary"],
+    "title_en": ["title_en", "name_en", "en_title", "en_name", "title", "title en"],
+    "title_ru": ["title_ru", "name_ru", "ru_title", "ru_name", "title ru"],
+    "short_en": ["short_en", "summary_en", "en_short", "en_summary", "short en"],
+    "short_ru": ["short_ru", "summary_ru", "ru_short", "ru_summary", "short ru"],
     "tags": ["tags", "labels", "categories"],
-    "bullets_en": ["bullets_en", "points_en", "en_bullets"],
-    "bullets_ru": ["bullets_ru", "points_ru", "ru_bullets"],
-    "examples_en": ["examples_en", "cases_en", "en_examples", "example_en"],
-    "examples_ru": ["examples_ru", "cases_ru", "ru_examples", "example_ru"],
+    "bullets_en": ["bullets_en", "points_en", "en_bullets", "bullets en"],
+    "bullets_ru": ["bullets_ru", "points_ru", "ru_bullets", "bullets ru"],
+    "examples_en": ["examples_en", "cases_en", "en_examples", "example_en", "examples en"],
+    "examples_ru": ["examples_ru", "cases_ru", "ru_examples", "example_ru", "examples ru"],
     "weight": ["weight", "order", "prio", "rank"],
     "pinned": ["pinned", "pin", "featured"],
 }
```

## Summary

**Files Changed:** 1
- `apps/miniapp-api/app/services/skills_loader.py` - Extended CSV header aliases

**Files Verified (No Changes):** 4
- `apps/miniapp-api/routers/skills.py` - API endpoints already correct
- `apps/miniapp-web/src/pages/SkillsPage.tsx` - Modal already uses correct classes
- `apps/miniapp-web/src/index.css` - Modal offset already configured
- `apps/miniapp-web/src/components/SkillDetail.tsx` - Component already handles bullets/examples

**New Files:** 2
- `SKILLS_CSV_ALIGNMENT_RUNBOOK.md` - Testing runbook with PowerShell and Bash commands
- `SKILLS_CSV_ALIGNMENT_CHANGELOG.md` - Detailed changelog

**Total Lines Changed:** 8 lines (added space-separated header aliases)

**Breaking Changes:** None

**Backward Compatibility:** Maintained - existing aliases preserved, new aliases added

