1) Backend: Added `apps/miniapp-api/routers/skills.py` with:
   - `GET /skills` — returns skills list (supports `?lang=ru|en` projection)
   - `GET /skills/{slug}` — returns detail for a single skill
   - Legacy aliases: `GET /rules` and `GET /rules/{slug}` mapping to the same handlers, with deprecation logs

2) Backend: Wired new router in `apps/miniapp-api/main.py`; removed hardcoded `/rules` and pointed alias to `/skills`.

3) Backend: Implemented Notion-backed fetch with seeds merge:
   - Uses `NOTION_DB_SKILLS` (or `NOTION_DB` fallback)
   - Accepts legacy schema by reading common property names
   - Merges with seeds in `apps/miniapp-api/seed/skills.en.json` and `skills.ru.json` (Notion takes precedence)

4) Frontend: Introduced skills routes in SPA:
   - `/skills` shows tiles (mobile-friendly)
   - `/skills/:slug` shows detail with bullets/examples and back navigation
   - Kept legacy adapter for `/rules` in API client during rollout

5) Frontend: Added types mirroring backend models and projected shapes.

6) Docs: Updated `README-miniapp.md` with migration notes and smoke test commands.

Acceptance quick checks:

```bash
curl -sS http://localhost:8081/skills | jq 'map(.slug) | .[0:6]'
curl -sS http://localhost:8081/skills/automation | jq '.title,.bullets[0]'
curl -sS http://localhost:8081/rules | jq 'length'
```


