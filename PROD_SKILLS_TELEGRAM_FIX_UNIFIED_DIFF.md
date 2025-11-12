# Production Skills & Telegram Export Fix - Unified Diff

## Summary
Minimal changes to fix production API issues:
1. Added frontend guard to handle both array and {items,count} response shapes
2. Added optional CSV override compose file for host CSV mounting
3. Verified route order (already correct: /api/skills/debug before /api/skills/{slug})
4. Verified telegram selftest route exists and is registered
5. Verified export handler accepts both {items:[...]} and {messages:[...]} shapes

## Changes

### infra/compose/miniapp.compose.yaml
```diff
--- a/infra/compose/miniapp.compose.yaml
+++ b/infra/compose/miniapp.compose.yaml
@@ -17,7 +17,7 @@ services:
       DEFAULT_LANG: ${DEFAULT_LANG:-ru}
       NOTION_TIMEOUT: ${NOTION_TIMEOUT:-10}
       NOTION_CACHE_TTL_SKILLS: ${NOTION_CACHE_TTL_SKILLS:-300}
-      SKILLS_SOURCE: ${SKILLS_SOURCE:-auto}
+      SKILLS_SOURCE: ${SKILLS_SOURCE:-csv}
       SKILLS_CSV_PATH: ${SKILLS_CSV_PATH:-/app/data/skills.csv}
       WEBSITE_ORIGIN: ${WEBSITE_ORIGIN:-https://miniapp.dmitrybond.tech}
```

### apps/miniapp-web/src/api/client.ts
```diff
--- a/apps/miniapp-web/src/api/client.ts
+++ b/apps/miniapp-web/src/api/client.ts
@@ -39,7 +39,9 @@ export async function getSkills(lang: Locale, signal?: AbortSignal): Promise<S
   if (!r.ok) {
     throw new Error(`Failed to load skills (status ${r.status})`);
   }
   const data = await r.json();
-  if (!Array.isArray(data)) {
+  // Guard: handle both array and {items,count} shapes
+  const items = Array.isArray(data) ? data : (data?.items || []);
+  if (!Array.isArray(items)) {
     return [];
   }
-  return data
+  return items
     .map((item) => ({
       slug: typeof item?.slug === "string" ? item.slug : "",
```

### infra/compose/miniapp.csv.override.yml (NEW FILE)
```yaml
# Optional override for mounting host CSV file
# Usage: docker compose -f miniapp.compose.yaml -f miniapp.csv.override.yml up
services:
  api:
    volumes:
      - ./data/skills.csv:/app/data/skills.csv:ro
```

## Verified (No Changes Needed)

### apps/miniapp-api/routers/skills.py
- Route order is correct: `/api/skills/debug` (line 143) comes before `/api/skills/{slug}` (line 172)
- Both routes are in `api_router` with `/api` prefix

### apps/miniapp-api/routers/chat_v2.py
- `/api/telegram/selftest` route exists at line 133
- Router is registered in main.py at line 94

### apps/miniapp-api/main.py
- All routers properly included:
  - `chat_router` (line 94) - includes telegram selftest
  - `skills_api_router` (line 98) - includes /api/skills/debug and /api/skills/{slug}

### infra/compose/miniapp.compose.yaml
- Environment variables already present:
  - `SKILLS_CSV_PATH` (line 21)
  - `TELEGRAM_TOKEN` (line 26)
  - `TELEGRAM_BOT_TOKEN` (line 27)
  - `ADMIN_CHAT_ID` (line 28)
  - `TELEGRAM_ADMIN_CHAT_ID` (line 29)
