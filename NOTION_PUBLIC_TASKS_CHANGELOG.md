# Notion Public Tasks Implementation - Changelog

## Summary

Replaced the stub endpoint `/api/tasks/public` (which returned `[]`) with a real Notion-backed implementation. The frontend Task Status modal now displays vertical cards with task information fetched from Notion.

## Changes

### 1. Created `apps/miniapp-api/integrations/notion_public.py`

New integration module providing:

- **Environment validation**: Reads and validates `NOTION_API_KEY`, `NOTION_PUBLIC_TASKS_DB_ID`, and `NOTION_TIMEOUT` (default 10s)
- **Schema resolution** (`resolve_schema`): Dynamically discovers database properties:
  - Title property (first `title` type property)
  - Public checkbox property (prefers "Public?" or "Public", falls back to any checkbox)
  - Status property (prefers `status` type, accepts `select` type)
  - Status values list
- **Description extraction** (`first_description`): Extracts first paragraph or bullet list item from page blocks (up to 240 chars, plain text)
- **Progress computation** (`compute_progress`): Calculates progress percentage from scope/done, with fallback to "Progress %" property (clamped 0-100)
- **Query function** (`query_public_tasks`):
  - Filters: `public=true` AND status in provided list (case-insensitive matching)
  - Default statuses: `["In Progress", "Review"]` if none provided
  - Limit: 20 (configurable, max 100)
  - Sort: `last_edited_time` descending
  - Maps properties: id, title, status, scope, done, progressPct, description, tags, reviewAt, lastUpdated, url
- **Pydantic model** (`PublicTaskOut`): Output model compatible with frontend `PublicTask` type

### 2. Updated `apps/miniapp_api/routers/public_tasks.py`

Replaced stub implementation with:

- **`GET /api/tasks/public`**:
  - Query parameters:
    - `statuses` (optional): Comma-separated status names (case-insensitive), defaults to "In Progress,Review"
    - `limit` (optional): Maximum number of tasks (1-100), defaults to 20
  - Error handling:
    - HTTP 500: Missing environment variables or integration not available
    - HTTP 502: Notion API failures
  - Returns: `List[PublicTaskOut]`

- **`GET /api/tasks/debug`**:
  - Returns schema information (no secrets):
    - `available`: Boolean indicating if integration is available
    - `title_prop`, `public_prop`, `status_prop`: Resolved property names
    - `status_type`: "status" or "select"
    - `status_values_count`: Number of available status values
    - `status_values`: List of status value names
  - Error handling: Returns error information in response body (does not raise exceptions)

### 3. Dependencies

- `notion-client==2.2.1` already present in `apps/miniapp-api/requirements.txt` (no change needed)

### 4. Frontend

- **No changes required**: Frontend already configured correctly:
  - `TasksModal.tsx` uses `fetchOpenTasks()` which calls `/api/tasks/public?statuses=In%20Progress,Review&limit=20`
  - `TaskCard.tsx` renders all required fields: title (link), status pill, scope/done, progress bar, description, tags, lastUpdated

## Technical Details

### Schema Discovery

The implementation dynamically discovers database schema properties rather than hardcoding property names:
- Searches for title property (type `title`)
- Searches for public checkbox (prefers names containing "public")
- Searches for status property (prefers `status` type, accepts `select` type)
- Searches for number properties containing "scope", "done", or "progress" in name
- Searches for `multi_select` property for tags
- Searches for `date` property for reviewAt

### Case-Insensitive Status Matching

Status filtering is case-insensitive:
- Input statuses are normalized (lowercased, trimmed)
- Matched against available status values from schema
- Returns tasks with matching statuses using actual case from database

### Error Handling

- **Missing env vars**: Raises `ValueError`, caught by router → HTTP 500
- **Notion API errors**: Raises `Exception` with message, caught by router → HTTP 502
- **Individual page conversion failures**: Logged as warnings, processing continues for other tasks

### Property Extraction

- **Title**: Extracted from title property rich_text array
- **Status**: Extracted from status/select property (supports both types)
- **Scope/Done**: Searched by name pattern (case-insensitive contains "scope"/"done")
- **Progress %**: Searched by name pattern (contains "progress" and "%"), used as fallback if scope/done unavailable
- **Tags**: First `multi_select` property found
- **ReviewAt**: First `date` property found
- **Description**: Extracted from page blocks (first paragraph or bullet list item)
- **URL**: Generated as `https://notion.so/{page_id_without_dashes}`

## Testing

### PR Runbook Commands

```bash
# Test debug endpoint (schema resolution)
curl -sS http://127.0.0.1:18080/api/tasks/debug | jq .

# Test public tasks endpoint (default statuses)
curl -sS "http://127.0.0.1:18080/api/tasks/public?statuses=In%20Progress,Review&limit=10" | jq .

# Test with custom statuses
curl -sS "http://127.0.0.1:18080/api/tasks/public?statuses=Backlog&limit=5" | jq .

# Test with limit
curl -sS "http://127.0.0.1:18080/api/tasks/public?limit=3" | jq .
```

### Expected Behavior

1. **Debug endpoint**: Returns schema information including property names and status values
2. **Public endpoint**: Returns list of tasks with `public=true` and matching statuses
3. **Empty result**: Returns `[]` if no matching tasks found
4. **Error cases**:
   - Missing env vars → HTTP 500 with error message
   - Notion API failure → HTTP 502 with error message
   - Invalid database schema → HTTP 500/502 depending on when error occurs

## Files Changed

1. `apps/miniapp-api/integrations/notion_public.py` (new file, 422 lines)
2. `apps/miniapp_api/integrations/notion_public.py` (new file, same content for development)
3. `apps/miniapp_api/routers/public_tasks.py` (replaced stub, 120 lines)

## Notes

- Dockerfile copies `apps/miniapp-api` to `apps/miniapp_api` at build time, so both directories contain the integration file
- Frontend Task Status modal already renders vertical cards correctly - no frontend changes needed
- Case-insensitive status matching allows flexible querying (e.g., "in progress" matches "In Progress")
- Default statuses ("In Progress", "Review") are applied when no statuses parameter is provided

