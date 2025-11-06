# Notion Tasks API Fix and Card Rendering - Changelog

## Summary
Fixed backend API to fail loudly on missing configuration, improved case-insensitive status filtering, added debug endpoint, and enhanced frontend card rendering with proper error handling.

## Changes

### Backend (apps/miniapp-api)

1. **Fixed `query_public_tasks()` to fail loudly on missing env vars**
   - Changed from returning empty list to raising `ValueError` when `NOTION_API_KEY` or `NOTION_PUBLIC_TASKS_DB_ID` are missing
   - Router now returns HTTP 500 for configuration errors

2. **Improved case-insensitive status filtering**
   - Added `_get_status_mapping()` function that retrieves actual status values from Notion DB
   - Builds a mapping from normalized (lowercase) status names to actual DB values
   - Status filtering now works case-insensitively by mapping input to actual DB values before querying

3. **Enhanced error handling**
   - Router returns HTTP 502 with safe message "Notion query failed" on API errors
   - Router returns HTTP 500 with "Notion configuration error" on missing env vars
   - Added proper exception handling for `APIResponseError` and other Notion errors

4. **Added debug endpoint**
   - New `GET /api/tasks/debug` endpoint returns configuration status and available status values
   - Does not expose secrets (only shows DB ID, not API key)
   - Useful for troubleshooting configuration issues

5. **Improved sorting robustness**
   - Checks if `Last Updated` property exists before using it in sort
   - Falls back to sorting by `last_edited_time` if property doesn't exist
   - Handles missing properties gracefully

### Frontend (apps/miniapp-web)

6. **Fixed TaskCard Scope/Done display**
   - Changed from "Scope {done}/{scope}" to "Scope X • Done Y" format
   - Handles cases where only one value is present
   - Shows proper formatting with bullet separator

7. **Added progress percentage label**
   - Progress bar now shows "Progress" label and percentage (e.g., "45%")
   - Displays above the progress bar for better visibility

8. **Improved error handling in TasksModal**
   - Replaced simple error text with styled error box
   - Shows friendly message: "Can't reach Notion right now"
   - Better UX with red background and border

9. **Enhanced loading state**
   - Replaced simple "Loading…" text with skeleton loader
   - Shows animated placeholder bars while fetching

10. **Improved date formatting**
    - Updated time display to show relative format: "Jan 15, 2:30 PM"
    - More readable than full ISO timestamp

## Files Changed

- `apps/miniapp-api/integrations/notion_public_tasks.py`
- `apps/miniapp-api/routers/public_tasks.py`
- `apps/miniapp-web/src/components/TaskCard.tsx`
- `apps/miniapp-web/src/components/TasksModal.tsx`

## Testing

To verify the changes:

```powershell
# Test backend (adjust host if needed)
curl "http://127.0.0.1:8080/api/tasks/public?statuses=In%20Progress,Review&limit=5"
curl "http://127.0.0.1:8080/api/tasks/debug"

# Test with missing env (should return 500)
# (temporarily unset NOTION_API_KEY to test)

# Test frontend
# Open miniapp and click Task Status button
# Verify cards show: title, status badge, progress bar with %, scope/done, description, updated time
```

## Acceptance Criteria Met

✅ GET /api/tasks/public returns non-empty array when tasks exist  
✅ Status filtering is case-insensitive (e.g., "in progress" matches "In Progress")  
✅ Returning objects include: id, title, status, scope, done, progressPct, description, updatedAt  
✅ Frontend modal shows vertical list of cards with all required fields  
✅ On missing env or Notion failure, API returns 500/502 with clear detail  
✅ Frontend shows friendly error message ("Can't reach Notion right now")

