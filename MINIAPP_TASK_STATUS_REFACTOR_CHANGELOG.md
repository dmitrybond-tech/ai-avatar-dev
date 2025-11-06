# MiniApp Task Status Refactor - Changelog

## Overview
Refactored the MiniApp UI to hide the Kanban board by default and show public open tasks in a modal when clicking "Task status". Updated header with avatar and "Dmitry's Assistant" text.

## Changes

### A) API: Support "open only" filter (server-side)

#### 1. `apps/miniapp-api/integrations/notion_public_tasks.py`
- **Modified `query_public_tasks()` function**:
  - Added `open_only: bool = True` parameter (defaults to True)
  - Added client-side filtering to exclude tasks where:
    - `status` is "Done" or "Closed", OR
    - `progressPct >= 100`
  - Filtering happens after fetching from Notion (maintains existing Public?=true filter)
  - Sorting remains: `lastUpdated desc, reviewAt asc`

#### 2. `apps/miniapp-api/routers/public_tasks.py`
- **Updated `GET /api/tasks/public` endpoint**:
  - Added `open_only: bool = Query(default=True)` query parameter
  - Passes `open_only` to `query_public_tasks()`
  - Maintains existing error handling (500 on exceptions)

**Acceptance**: 
- `curl http://127.0.0.1:18080/api/tasks/public` returns only open tasks (Public?=true AND not Done/Closed AND progress < 100)
- `curl http://127.0.0.1:18080/api/tasks/public?open_only=false` returns all public tasks

---

### B) Web: Move tasks out of main screen; show in modal/panel

#### 3. `apps/miniapp-web/src/shared/api/tasks.ts`
- **Added `fetchOpenTasks()` function**:
  - Calls `/api/tasks/public?open_only=1`
  - Returns `Promise<PublicTask[]>`
  - Uses existing `PublicTask` type
  - Keeps existing `fetchPublicTasks()` unchanged (for backward compatibility)

#### 4. `apps/miniapp-web/src/components/TasksList.tsx` (NEW)
- **New component** that displays tasks as cards (not columns):
  - Fetches open tasks on mount using `fetchOpenTasks()`
  - States: `loading`, `error`, `items`
  - Card layout per task:
    - Title (link to Notion URL, opens in new tab)
    - Status chip (small badge)
    - Progress bar (0-100%)
    - Tags (small pills)
    - Review date (highlighted if overdue) or relative last updated time
  - Empty state: "Nothing in progress yet."
  - Loading skeletons
  - Error display

#### 5. `apps/miniapp-web/src/components/TasksModal.tsx` (NEW)
- **New modal component**:
  - Fixed overlay with backdrop (click to close)
  - Modal content with header ("Task status") and close button (×)
  - Scrollable content area containing `TasksList`
  - Tailwind styling (minimal, responsive)
  - Prevents event propagation on modal content

#### 6. `apps/miniapp-web/src/App.tsx`
- **Removed `TasksBoard` from default home view**:
  - Removed `import TasksBoard` and its rendering
  - Removed `'tasks'` from view state type (now only `'home'|'skills'`)
  - Removed the `'tasks'` view case entirely
- **Added modal state management**:
  - Added `isTasksOpen` state
  - Wired "Task status" button to open modal: `onTasks={() => setIsTasksOpen(true)}`
  - Added `<TasksModal>` component at root level
- **Kept chat and other buttons unchanged**

**Acceptance**:
- On app load, no board/columns are visible
- Clicking "Task status" opens modal with list of public, open tasks as cards
- Modal can be closed via backdrop click or × button

---

### C) Header avatar & title

#### 7. `apps/miniapp-web/src/App.tsx` (header section)
- **Updated header text**: Changed "Дима's Assistant" → "Dmitry's Assistant"
- **Added circular avatar**:
  - Uses `/icons/android-chrome-192x192.png` from public folder
  - Rendered as 40px (h-10 w-10) circle with `rounded-full`
  - `object-cover` to maintain aspect ratio
  - `loading="eager"` and `decoding="async"` for performance
  - Positioned immediately left of heading text
  - Maintains layout on narrow screens (flex with gap)

**Acceptance**:
- Header shows circular avatar + "Dmitry's Assistant" text
- No layout shift on image load

---

## Files Modified

### API Files
1. `apps/miniapp-api/integrations/notion_public_tasks.py`
2. `apps/miniapp-api/routers/public_tasks.py`

### Web Files
3. `apps/miniapp-web/src/shared/api/tasks.ts`
4. `apps/miniapp-web/src/App.tsx`
5. `apps/miniapp-web/src/components/TasksList.tsx` (NEW)
6. `apps/miniapp-web/src/components/TasksModal.tsx` (NEW)

---

## Notes

- **Backward compatibility**: `fetchPublicTasks()` still exists for any code that might use it
- **TasksBoard component**: Removed from rendering but file remains in codebase (not deleted)
- **Old Tasks.tsx**: Component still exists but is no longer used (old API endpoint)
- **No Caddy changes**: Caddyfile untouched as required
- **TypeScript strict**: All changes pass type checking
- **No regressions**: Chat, "Book a meeting", and "What I can do?" buttons remain functional

---

## Testing

### API Testing
```bash
# Should return only open tasks
curl -sS http://127.0.0.1:18080/api/tasks/public | jq .

# Should return all public tasks
curl -sS http://127.0.0.1:18080/api/tasks/public?open_only=false | jq .
```

### UI Testing
1. Load app → no board visible
2. Click "Task status" → modal opens with task cards
3. Verify cards show: title (link), status, progress, tags, dates
4. Verify header shows avatar + "Dmitry's Assistant"
5. Verify other buttons still work

---

## Build & Deployment

- No CI changes required
- Build remains deterministic
- No secrets exposed
- FastAPI handles boolean query params correctly (`?open_only=1` works)

