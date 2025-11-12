# Grok Integration Unified Diffs

## 1. apps/miniapp-api/requirements.txt

```diff
--- a/apps/miniapp-api/requirements.txt
+++ b/apps/miniapp-api/requirements.txt
@@ -15,4 +15,5 @@ python-multipart==0.0.9
 email-validator==2.2.0
 sentence-transformers==3.0.1
 faiss-cpu==1.8.0
 python-dotenv==1.0.1
-rapidfuzz==3.6.1
+rapidfuzz==3.9.6
+xai-sdk==1.4.0
 pandas==2.2.2
```

## 2. infra/compose/miniapp.llm.override.yml (new file)

```yaml
services:
  api:
    env_file:
      - .env.miniapp
    environment:
      LLM_PROVIDER: ${LLM_PROVIDER:-grok}
      GROK_MODEL: ${GROK_MODEL:-grok-4}
      GROK_BASE_URL: ${GROK_BASE_URL:-https://api.x.ai}
      GROK_MAX_TOKENS: ${GROK_MAX_TOKENS:-512}
      GROK_TEMPERATURE: ${GROK_TEMPERATURE:-0.3}
      XAI_API_KEY: ${XAI_API_KEY}

  bot:
    env_file:
      - .env.miniapp
    environment:
      LLM_PROVIDER: ${LLM_PROVIDER:-grok}
      GROK_MODEL: ${GROK_MODEL:-grok-4}
      GROK_BASE_URL: ${GROK_BASE_URL:-https://api.x.ai}
      GROK_MAX_TOKENS: ${GROK_MAX_TOKENS:-512}
      GROK_TEMPERATURE: ${GROK_TEMPERATURE:-0.3}
      XAI_API_KEY: ${XAI_API_KEY}
```

## 3. apps/miniapp-api/app/services/skills_loader.py (new file)

See full file content - 339 lines implementing:
- CSV loading with UTF-8 BOM handling
- mtime-based caching
- Fuzzy search using rapidfuzz
- SkillRecord class with language-aware methods
- SkillsLoader class with thread-safe caching

## 4. apps/miniapp-api/app/services/llm_grok.py (new file)

See full file content - 120 lines implementing:
- GrokClient wrapper for xAI SDK
- ask_grok() and ask_with_context() methods
- Environment variable reading
- Error handling and timeout support

## 5. apps/miniapp-api/routers/skills.py

```diff
--- a/apps/miniapp-api/routers/skills.py
+++ b/apps/miniapp-api/routers/skills.py
@@ -1,9 +1,15 @@
 from __future__ import annotations
 
+import logging
 import os
 from pathlib import Path
 from typing import Any, Dict, List, Optional
 
 from fastapi import APIRouter, HTTPException, Query, Request
+from pydantic import BaseModel
+
+from ..services.skills import SkillRecord, SkillsRepository
+from ..services.skills_loader import get_loader
+from ..services.llm_grok import get_grok_client
 
+logger = logging.getLogger(__name__)
 router = APIRouter(tags=["skills"])
 api_router = APIRouter(prefix="/api", tags=["skills"])
 alias_router = APIRouter(tags=["legacy-rules"])
@@ -47,6 +53,20 @@ def _project_detail(skill: SkillRecord, lang: str) -> Dict[str, Any]:
     }
 
 
+def _check_csv_source(request: Request) -> None:
+    """Check if CSV source is required and file exists; raise 503 if missing."""
+    source = os.getenv("SKILLS_SOURCE", "auto").strip().lower()
+    if source == "csv":
+        csv_path_env = os.getenv("SKILLS_CSV_PATH")
+        if csv_path_env:
+            csv_path = Path(csv_path_env)
+        else:
+            csv_path = Path("/app/data/skills.csv")
+        if not csv_path.exists():
+            raise HTTPException(
+                status_code=503,
+                detail=f"Skills CSV file not found at {csv_path}. Service unavailable."
+            )
+
+
 def _list_skills_impl(request: Request, lang: Optional[str]) -> List[Dict[str, Any]]:
+    _check_csv_source(request)
     repo = _repo(request)
     snapshot = repo.snapshot()
     skills = snapshot.skills
@@ -98,6 +118,7 @@ def _get_skill_impl(
     slug: str,
     request: Request,
     lang: Optional[str],
 ) -> Dict[str, Any]:
+    _check_csv_source(request)
     repo = _repo(request)
     snapshot = repo.snapshot()
     skill = next((item for item in snapshot.skills if item.key == slug), None)
@@ -205,6 +226,7 @@ def search_skills_api(
     lang: Optional[str] = Query(default=None, description="ru|en for projected payload"),
     limit: int = Query(default=10, ge=1, le=50, description="Max number of results"),
 ) -> List[Dict[str, Any]]:
+    _check_csv_source(request)
     repo = _repo(request)
     lang_key = _lang_key(lang) if lang else "en"
     top_skills = repo.relevant_skills(q, top_k=limit)
@@ -220,3 +242,88 @@ def search_skills_api(
         }
         for skill in top_skills
     ]
+
+
+# Request/Response models for /api/skills/ask
+class AskRequest(BaseModel):
+    q: str
+    lang: Optional[str] = None
+    selected: Optional[List[str]] = None
+
+
+class AskResponse(BaseModel):
+    answer: str
+    used_skills: List[str]
+    model: str
+    tokens_estimate: int
+
+
+@api_router.post("/skills/ask", response_model=AskResponse)
+def ask_skills(request: Request, body: AskRequest) -> AskResponse:
+    """Ask Grok about skills based on user question."""
+    _check_csv_source(request)
+
+    # Check if Grok is available
+    grok_client = get_grok_client()
+    if not grok_client.available:
+        api_key_set = bool(os.getenv("XAI_API_KEY"))
+        if not api_key_set:
+            raise HTTPException(status_code=401, detail="XAI_API_KEY not configured")
+        raise HTTPException(status_code=502, detail="Grok provider unavailable")
+
+    # Load skills using the loader
+    loader = get_loader()
+    skills = loader.load_skills()
+    if not skills:
+        raise HTTPException(status_code=503, detail="No skills available")
+
+    # Determine language
+    lang = body.lang or "en"
+    lang_key = _lang_key(lang)
+
+    # Find relevant skills
+    query = body.q.strip()
+    if not query:
+        raise HTTPException(status_code=400, detail="Query 'q' cannot be empty")
+
+    # Use selected skills if provided, otherwise search
+    if body.selected:
+        selected_skills = [s for s in skills if s.key in body.selected]
+        if not selected_skills:
+            # Fallback to search if selected not found
+            selected_skills = loader.search_skills(query, lang=lang_key, top_k=5)
+    else:
+        selected_skills = loader.search_skills(query, lang=lang_key, top_k=5)
+
+    if not selected_skills:
+        selected_skills = skills[:3]  # Fallback to first 3 skills
+
+    # Build skills context string
+    context_parts = []
+    for skill in selected_skills[:5]:  # Limit to top 5
+        skill_info = [
+            f"Skill: {skill.title(lang_key)}",
+            f"Summary: {skill.summary(lang_key)}",
+        ]
+        if skill.tags:
+            skill_info.append(f"Tags: {', '.join(skill.tags)}")
+        if skill.bullets(lang_key):
+            bullets_text = "; ".join(skill.bullets(lang_key)[:3])
+            skill_info.append(f"Capabilities: {bullets_text}")
+        if skill.examples(lang_key):
+            examples_text = "; ".join(skill.examples(lang_key)[:2])
+            skill_info.append(f"Examples: {examples_text}")
+        context_parts.append("\n".join(skill_info))
+
+    skills_context = "\n\n".join(context_parts)
+
+    # Call Grok
+    try:
+        answer = grok_client.ask_with_context(
+            user_question=query,
+            skills_context=skills_context,
+        )
+        if not answer:
+            raise HTTPException(status_code=502, detail="Grok provider returned empty response")
+    except HTTPException:
+        raise
+    except Exception as exc:
+        logger.error("Grok API call failed: %s", exc, exc_info=True)
+        raise HTTPException(status_code=502, detail="Grok provider error; try again later")
+
+    # Estimate tokens (rough: ~4 chars per token)
+    tokens_estimate = len(query) + len(skills_context) + len(answer or "")
+    tokens_estimate = tokens_estimate // 4
+
+    return AskResponse(
+        answer=answer or "No answer generated",
+        used_skills=[s.key for s in selected_skills],
+        model=grok_client._model,
+        tokens_estimate=tokens_estimate,
+    )
```

## 6. apps/miniapp-bot/main.py

Key changes:
- Added `import httpx`
- Added `_smart_llm_toggle: dict[int, bool]` for per-user toggle state
- Added `get_smart_llm_enabled()` and `set_smart_llm_enabled()` helpers
- Added `build_smart_llm_toggle()` function
- Added `API_BASE_URL` env var
- Added `/smart` command handler
- Added `on_smart_llm_toggle()` callback handler
- Added `_call_skills_ask_api()` function
- Added `on_text_message()` handler for Smart LLM integration

See full diff for complete changes (approximately 100+ lines added/modified).

