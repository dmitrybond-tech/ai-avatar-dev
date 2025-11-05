# MiniApp – Notion Public Tasks & Tasks Board

1. API deps pinned
   - apps/miniapp-api/requirements.txt: notion-client==2.2.4 (Py3.11+), pydantic already v2.

2. API integration (miniapp-api)
   - Added apps/miniapp-api/integrations/notion_public_tasks.py
     - Reads env: NOTION_API_KEY, NOTION_PUBLIC_TASKS_DB_ID=2a24b952b70580e398ab000c43eea798, NOTION_TIMEOUT (default 10)
     - Models: PublicTaskOut, PublicTaskCreate, PublicTaskUpdate
     - Helpers: compute_progress, set_status_property (status/select dual support), assert_schema()
     - CRUD: query_public_tasks, create_task, update_task, add_comment
   - Added apps/miniapp-api/routers/public_tasks.py
     - Routes under /api/tasks: GET /public, POST /, PATCH /{id}, POST /{id}/comment
     - Startup: assert_schema() (log-only on mismatch)
   - Wired router in apps/miniapp-api/main.py with prefix "/api"

3. Web client & UI
   - New client: apps/miniapp-web/src/shared/api/tasks.ts
     - export type PublicTask; fetchPublicTasks() calls `${VITE_API_BASE_URL}/api/tasks/public`
   - New component: apps/miniapp-web/src/components/TasksBoard.tsx
     - Groups by status, shows cards with title, progress bar, tags, updated/review dates
     - Loading skeletons and compact error state
   - Rendered <TasksBoard /> on home screen below the input (apps/miniapp-web/src/App.tsx)
   - Env: apps/miniapp-web/env.example already contains VITE_API_BASE_URL=https://miniapp.dmitrybond.tech

4. Health & smoke targets
   - OpenAPI contains /api/tasks/public (served by miniapp-api)
   - curl http://127.0.0.1:18080/api/tasks/public → 200 JSON
   - curl https://miniapp.dmitrybond.tech/api/tasks/public → 200 JSON

5. Notes
   - CORS: existing allowlist includes https://miniapp.dmitrybond.tech
   - Secrets are only via env; none committed
   - No Caddy changes required


