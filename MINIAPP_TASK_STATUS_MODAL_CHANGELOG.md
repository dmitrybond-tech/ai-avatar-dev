# Task Status Modal - Notion Cards Integration Changelog

**Date:** 2025-01-XX  
**Version:** v0.2.0  
**Scope:** Show Notion task cards in Task status modal with vertical card layout

---

## Summary

Implemented vertical card display for public Notion tasks in the Task Status modal. The API now fetches tasks from Notion with full field mapping including description extraction from page blocks, and the web modal renders each task as a vertical card with title, status, scope/done, progress bar, description snippet, tags, and last updated timestamp.

---

## Changes

### 1. API Integration (`apps/miniapp-api/integrations/notion_public_tasks.py`)

#### Added Fields to `PublicTaskOut` Model
- `scope: Optional[int]` - Scope value from Notion
- `done: Optional[int]` - Done value from Notion  
- `description: Optional[str]` - Description snippet (≤240 chars)

#### New Helper Functions
- `get_status_property(props: dict) -> Optional[str]` - Returns 'status', 'select', or None
- `page_url(page_id: str) -> str` - Generates Notion page URL from page_id
- `extract_description(page_id: str, client: Client) -> Optional[str]` - Extracts description from:
  1. Description property (rich_text) if available
  2. Falls back to first paragraph or bulleted_list_item from page blocks
  3. Returns first 240 chars, stripped of newlines/markdown

#### Updated Functions
- `compute_progress()` - Now accepts `fallback_pct` parameter to use Progress % property when scope/done are missing
- `_page_to_out()` - Now accepts optional `client` parameter for description extraction, includes scope/done/progress_pct_prop mapping
- `query_public_tasks()` - Enhanced with:
  - `statuses: Optional[List[str]]` parameter for status filtering
  - Default statuses `["In Progress", "Review"]` when `open_only=True` and no statuses specified
  - Robust Notion filter building using "or" conditions for multiple statuses
  - Case-insensitive client-side status filtering
  - Fail-soft behavior: returns empty list with warning if env vars missing

#### Property Constants
- Added `PROP_DESCRIPTION = "Description"` constant

#### Status Property Handling
- Replaced `_status_property_name_and_type()` with `get_status_property()` for cleaner API
- Updated `_load_db_status_type()` to use new helper

---

### 2. API Router (`apps/miniapp-api/routers/public_tasks.py`)

#### Updated Endpoint: `GET /api/tasks/public`
- Added `statuses: Optional[str]` query parameter (CSV format, e.g., "In Progress,Review")
- Added `limit: int` query parameter (default=20, range 1-100)
- Updated `open_only: bool` parameter description
- Parses CSV statuses → list, strips spaces
- Defaults to `["In Progress", "Review"]` when `open_only=True` and no statuses provided
- Passes parsed parameters to `query_public_tasks()`

---

### 3. Docker Compose (`infra/compose/miniapp.compose.yaml`)

**Status:** ✅ Already configured

The compose file already includes all required environment variables:
- `NOTION_API_KEY=${NOTION_API_KEY}`
- `NOTION_PUBLIC_TASKS_DB_ID=${NOTION_PUBLIC_TASKS_DB_ID}`
- `NOTION_TIMEOUT=${NOTION_TIMEOUT:-10}`
- `WEBSITE_ORIGIN=${WEBSITE_ORIGIN:-https://miniapp.dmitrybond.tech}`

No changes needed.

---

### 4. Web API Client (`apps/miniapp-web/src/shared/api/tasks.ts`)

#### Updated `PublicTask` Type
- Added `scope?: number | null`
- Added `done?: number | null`
- Added `description?: string | null`

#### Updated `fetchOpenTasks()` Function
- Changed endpoint to include default statuses: `/api/tasks/public?statuses=In%20Progress,Review&limit=20`
- Uses URL-encoded status names for proper query parameter handling

---

### 5. Web Components

#### New Component: `apps/miniapp-web/src/components/TaskCard.tsx`
- Vertical card layout with:
  - Title and status badge in header
  - Description snippet (line-clamp-3, max 3 lines)
  - Scope/done display (e.g., "Scope 5/10")
  - Last updated timestamp
  - Progress bar (0-100%)
  - Tags as small badges
- Clickable card that links to Notion page
- Hover effects and transitions
- Responsive design with Tailwind classes

#### Updated Component: `apps/miniapp-web/src/components/TasksModal.tsx`
- Replaced `TasksList` component with direct `TaskCard` rendering
- Fetches tasks using `fetchOpenTasks()` on modal open
- Loading state: "Loading…" message
- Error state: Red error message
- Empty state: "Nothing in progress yet." when API returns []
- Vertical list: `space-y-3` gap between cards
- Responsive modal: full-width on mobile, max-w-2xl on desktop
- Fetches data only when modal is open (`useEffect` dependency on `isOpen`)

---

## API Behavior

### Default Filtering
- **Public?** = true (always required)
- **Status** in {In Progress, Review} (when `open_only=true` and no `statuses` param)
- **progressPct** < 100 (client-side filter when `open_only=true`)
- Excludes "Done" and "Closed" statuses (client-side filter when `open_only=true`)

### Query Parameters
- `statuses` (optional, CSV): Filter by specific status names
- `open_only` (default: true): Exclude completed tasks
- `limit` (default: 20, max: 100): Maximum number of tasks to return

### Sorting
- Primary: Last Updated (descending)
- Secondary: Review At (ascending)

### Error Handling
- Missing `NOTION_API_KEY` or `NOTION_PUBLIC_TASKS_DB_ID`: Returns [] with warning log
- Notion API errors: Returns HTTP 500 with concise error message
- Description extraction failures: Silently returns None (description optional)

---

## Testing

### Manual Smoke Tests

1. **API Endpoint**
   ```bash
   curl -sS http://127.0.0.1:18080/api/tasks/public | jq .
   curl -sS "http://127.0.0.1:18080/api/tasks/public?statuses=In%20Progress,Review&limit=20" | jq .
   ```

2. **Web Modal**
   - Open MiniApp
   - Click "Task status" button
   - Verify vertical cards display with:
     - Title links to Notion page
     - Status badge
     - Description snippet (if available)
     - Scope/done ratio
     - Progress bar
     - Tags
     - Last updated timestamp

### Expected Response Format
```json
[
  {
    "id": "page-id-here",
    "title": "Task Title",
    "status": "In Progress",
    "scope": 10,
    "done": 5,
    "progressPct": 50,
    "description": "First 240 chars of description...",
    "tags": ["tag1", "tag2"],
    "reviewAt": "2025-01-15T00:00:00Z",
    "lastUpdated": "2025-01-14T12:00:00Z",
    "url": "https://notion.so/pageidhere"
  }
]
```

---

## Acceptance Criteria ✅

- [x] GET /api/tasks/public returns array with all required fields
- [x] Default server filter: Public?=true and Status in {In Progress, Review}
- [x] Modal displays vertical list of cards
- [x] Each card shows: title, status, scope/done, progress bar, description snippet, tags, lastUpdated
- [x] Title links to Notion page
- [x] Empty state renders "Nothing in progress yet." when API returns []
- [x] No board visible by default on main screen
- [x] Build succeeds, type checks pass
- [x] No Caddy changes
- [x] No heavy UI libraries added
- [x] Description limited to 240 chars for safety

---

## Files Modified

1. `apps/miniapp-api/integrations/notion_public_tasks.py` - Enhanced Notion integration
2. `apps/miniapp-api/routers/public_tasks.py` - Added statuses query param
3. `apps/miniapp-web/src/shared/api/tasks.ts` - Extended PublicTask type
4. `apps/miniapp-web/src/components/TaskCard.tsx` - **NEW** - Vertical card component
5. `apps/miniapp-web/src/components/TasksModal.tsx` - Updated to render TaskCard list

---

## Dependencies

- **Python**: 3.11+ (already required)
- **notion-client**: 2.2.1 (already pinned)
- **Pydantic**: 2.x (already pinned)
- **TypeScript**: Strict mode (already enabled)
- **Tailwind CSS**: Already configured

---

## Notes

- Description extraction is best-effort: tries Description property first, then page blocks
- Status filtering supports both "status" and "select" property types in Notion
- Progress calculation uses scope/done if available, falls back to Progress % property
- All Notion API calls are wrapped in try/except for graceful degradation
- Client-side filtering ensures case-insensitive status matching
- Modal only fetches data when opened (performance optimization)

---

## Future Enhancements (Out of Scope)

- Pagination in modal
- Status filter dropdown in UI
- Refresh button
- Task detail view
- Real-time updates via WebSocket

