# Notion Public Tasks Implementation

## Summary

Replaced stub endpoint `/api/tasks/public` with real Notion-backed implementation. Frontend Task Status modal now displays vertical cards with task information from Notion.

## Implementation Complete

✅ Created `apps/miniapp-api/integrations/notion_public.py`  
✅ Created `apps/miniapp_api/integrations/notion_public.py` (for development)  
✅ Updated `apps/miniapp_api/routers/public_tasks.py`  
✅ Verified frontend already configured correctly  
✅ `notion-client==2.2.1` already in requirements.txt  

## PR Runbook

### Test Debug Endpoint

```bash
curl -sS http://127.0.0.1:18080/api/tasks/debug | jq .
```

**Expected**: Returns schema information including property names and status values.

### Test Public Tasks Endpoint

```bash
curl -sS "http://127.0.0.1:18080/api/tasks/public?statuses=In%20Progress,Review&limit=10" | jq .
```

**Expected**: Returns list of public tasks with matching statuses.

### Additional Test Cases

```bash
# Test with default statuses (no parameter)
curl -sS "http://127.0.0.1:18080/api/tasks/public?limit=5" | jq .

# Test with single status
curl -sS "http://127.0.0.1:18080/api/tasks/public?statuses=Backlog&limit=3" | jq .

# Test case-insensitive status matching
curl -sS "http://127.0.0.1:18080/api/tasks/public?statuses=in%20progress,review&limit=5" | jq .
```

## Files Changed

1. **New**: `apps/miniapp-api/integrations/notion_public.py` (422 lines)
2. **New**: `apps/miniapp_api/integrations/notion_public.py` (422 lines, same content)
3. **Modified**: `apps/miniapp_api/routers/public_tasks.py` (replaced stub, 120 lines)

## Key Features

- **Dynamic schema discovery**: Automatically finds database properties
- **Case-insensitive status matching**: Flexible querying
- **Default statuses**: "In Progress" and "Review" when none provided
- **Error handling**: HTTP 500 for missing env, HTTP 502 for Notion API failures
- **Progress calculation**: From scope/done or "Progress %" property
- **Description extraction**: First paragraph/bullet from page blocks (240 chars)

## Environment Variables Required

- `NOTION_API_KEY`: Notion API key
- `NOTION_PUBLIC_TASKS_DB_ID`: Notion database ID
- `NOTION_TIMEOUT`: Timeout in seconds (default: 10)

## Frontend

No changes needed - `TasksModal.tsx` and `TaskCard.tsx` already render vertical cards correctly.

## See Also

- `NOTION_PUBLIC_TASKS_CHANGELOG.md` - Detailed changelog
- `NOTION_PUBLIC_TASKS_IMPLEMENTATION.diff` - Unified diff (if needed)

