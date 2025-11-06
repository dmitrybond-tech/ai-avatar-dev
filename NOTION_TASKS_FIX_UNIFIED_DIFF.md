# Notion Tasks API Fix - Unified Diff

## File: apps/miniapp-api/integrations/notion_public_tasks.py

### Added: _get_status_mapping() function (after line 241)

```python
def _get_status_mapping(c: Client) -> Tuple[bool, dict]:
    """
    Retrieve database and build case-insensitive status mapping.
    Returns (is_status_type, mapping_dict) where mapping_dict maps normalized status names to actual DB values.
    """
    db = c.databases.retrieve(database_id=NOTION_PUBLIC_TASKS_DB_ID)
    props = db.get("properties", {})
    status_prop = props.get(PROP_STATUS, {})
    prop_type = status_prop.get("type")
    is_status_type = prop_type == "status"
    
    # Build mapping: normalized (lowercase, trimmed) -> actual status name
    status_mapping = {}
    if is_status_type:
        options = status_prop.get("status", {}).get("options", [])
        for opt in options:
            actual_name = opt.get("name", "").strip()
            if actual_name:
                normalized = actual_name.strip().lower()
                status_mapping[normalized] = actual_name
    else:
        options = status_prop.get("select", {}).get("options", [])
        for opt in options:
            actual_name = opt.get("name", "").strip()
            if actual_name:
                normalized = actual_name.strip().lower()
                status_mapping[normalized] = actual_name
    
    return is_status_type, status_mapping
```

### Modified: query_public_tasks() function

**Before (lines 256-266):**
```python
    if not NOTION_PUBLIC_TASKS_DB_ID:
        import warnings
        warnings.warn("NOTION_PUBLIC_TASKS_DB_ID not set, returning empty list", UserWarning)
        return []
    
    try:
        c = _client()
    except ValueError:
        import warnings
        warnings.warn("NOTION_API_KEY not set, returning empty list", UserWarning)
        return []
```

**After:**
```python
    if not NOTION_PUBLIC_TASKS_DB_ID:
        raise ValueError("NOTION_PUBLIC_TASKS_DB_ID is not configured")
    
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY is not configured")
    
    try:
        c = _client()
    except ValueError as e:
        raise ValueError(f"Failed to initialize Notion client: {e}")
```

**Before (line 268):**
```python
    is_status_type = _load_db_status_type(c)
```

**After:**
```python
    try:
        is_status_type, status_mapping = _get_status_mapping(c)
    except APIResponseError as e:
        raise Exception(f"Notion query failed: {e}")
    except Exception as e:
        raise Exception(f"Failed to retrieve database schema: {e}")
```

**Before (lines 274-309):**
```python
    # Add status filter if statuses provided
    if statuses:
        # Normalize status names (case-insensitive)
        statuses_normalized = [s.strip() for s in statuses if s.strip()]
        if statuses_normalized:
            # Use "or" filter for multiple statuses (Notion API supports this)
            if is_status_type:
                status_conditions = [
                    {"property": PROP_STATUS, "status": {"equals": s}}
                    for s in statuses_normalized
                ]
            else:
                status_conditions = [
                    {"property": PROP_STATUS, "select": {"equals": s}}
                    for s in statuses_normalized
                ]
            if len(status_conditions) == 1:
                filters.append(status_conditions[0])
            else:
                filters.append({"or": status_conditions})
    elif open_only:
        # Default to ["In Progress", "Review"] when open_only=True and no statuses specified
        default_statuses = ["In Progress", "Review"]
        if is_status_type:
            status_conditions = [
                {"property": PROP_STATUS, "status": {"equals": s}}
                for s in default_statuses
            ]
        else:
            status_conditions = [
                {"property": PROP_STATUS, "select": {"equals": s}}
                for s in default_statuses
            ]
        if len(status_conditions) == 1:
            filters.append(status_conditions[0])
        else:
            filters.append({"or": status_conditions})
```

**After:**
```python
    # Normalize and map statuses to actual DB values
    statuses_to_query: List[str] = []
    if statuses:
        # Normalize input statuses and map to actual DB values
        for s in statuses:
            normalized = s.strip().lower()
            if normalized and normalized in status_mapping:
                statuses_to_query.append(status_mapping[normalized])
    elif open_only:
        # Default to ["In Progress", "Review"] when open_only=True and no statuses specified
        default_normalized = ["in progress", "review"]
        for norm in default_normalized:
            if norm in status_mapping:
                statuses_to_query.append(status_mapping[norm])
    
    # Add status filter if we have statuses to query
    if statuses_to_query:
        if is_status_type:
            status_conditions = [
                {"property": PROP_STATUS, "status": {"equals": s}}
                for s in statuses_to_query
            ]
        else:
            status_conditions = [
                {"property": PROP_STATUS, "select": {"equals": s}}
                for s in statuses_to_query
            ]
        if len(status_conditions) == 1:
            filters.append(status_conditions[0])
        else:
            filters.append({"or": status_conditions})
```

**Before (lines 314-332):**
```python
    results: List[dict] = []
    has_more, cursor = True, None
    while has_more and len(results) < limit:
        query_params = {
            "database_id": NOTION_PUBLIC_TASKS_DB_ID,
            "filter": query_filter,
            "sorts": [
                {"property": PROP_LAST_UPDATED, "direction": "descending"},
                {"property": PROP_REVIEW_AT, "direction": "ascending"},
            ],
            "page_size": min(limit - len(results), 100),
        }
        if cursor:
            query_params["start_cursor"] = cursor
        
        resp = c.databases.query(**query_params)
        results.extend(resp.get("results", []))
        has_more = resp.get("has_more", False)
        cursor = resp.get("next_cursor")
```

**After:**
```python
    results: List[dict] = []
    has_more, cursor = True, None
    try:
        # Try to get database to check if PROP_LAST_UPDATED exists and is sortable
        db = c.databases.retrieve(database_id=NOTION_PUBLIC_TASKS_DB_ID)
        props = db.get("properties", {})
        has_last_updated = PROP_LAST_UPDATED in props
        
        while has_more and len(results) < limit:
            query_params = {
                "database_id": NOTION_PUBLIC_TASKS_DB_ID,
                "filter": query_filter,
                "page_size": min(limit - len(results), 100),
            }
            # Only add sort if property exists
            if has_last_updated:
                query_params["sorts"] = [
                    {"property": PROP_LAST_UPDATED, "direction": "descending"},
                ]
            if cursor:
                query_params["start_cursor"] = cursor
            
            resp = c.databases.query(**query_params)
            results.extend(resp.get("results", []))
            has_more = resp.get("has_more", False)
            cursor = resp.get("next_cursor")
        
        # Sort by last_edited_time if PROP_LAST_UPDATED wasn't available
        if not has_last_updated:
            results.sort(key=lambda p: p.get("last_edited_time", ""), reverse=True)
    except APIResponseError as e:
        raise Exception(f"Notion query failed: {e}")
    except Exception as e:
        raise Exception(f"Failed to query Notion database: {e}")
```

**Before (lines 334-335):**
```python
    # Convert pages to PublicTaskOut, extracting descriptions
    tasks = [_page_to_out(p, is_status_type, client=c) for p in results[:limit]]
```

**After:**
```python
    # Convert pages to PublicTaskOut, extracting descriptions
    tasks = []
    for p in results[:limit]:
        try:
            tasks.append(_page_to_out(p, is_status_type, client=c))
        except Exception as e:
            # Log but continue processing other tasks
            import logging
            logging.warning(f"Failed to convert page {p.get('id', 'unknown')}: {e}")
            continue
```

**Removed (lines 344-347):**
```python
    # Case-insensitive status filtering if statuses were provided
    if statuses:
        statuses_normalized = [s.strip().lower() for s in statuses if s.strip()]
        tasks = [t for t in tasks if t.status.strip().lower() in statuses_normalized]
```

**After (lines 389-392):**
```python
    # Final case-insensitive status filtering if statuses were provided (double-check)
    if statuses:
        statuses_normalized = [s.strip().lower() for s in statuses if s.strip()]
        tasks = [t for t in tasks if t.status.strip().lower() in statuses_normalized]
```

---

## File: apps/miniapp-api/routers/public_tasks.py

### Added imports (after line 4):
```python
from notion_client import APIResponseError
```

### Added imports (after line 15):
```python
    NOTION_PUBLIC_TASKS_DB_ID,
    _get_status_mapping,
    _client,
```

### Modified: list_public_tasks() error handling

**Before (lines 54-55):**
```python
        return query_public_tasks(limit=limit, statuses=parsed_statuses, open_only=open_only)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**After:**
```python
        return query_public_tasks(limit=limit, statuses=parsed_statuses, open_only=open_only)
    except ValueError as e:
        # Missing configuration - return 500
        raise HTTPException(status_code=500, detail="Notion configuration error")
    except APIResponseError as e:
        # Notion API error - return 502
        raise HTTPException(status_code=502, detail="Notion query failed")
    except Exception as e:
        # Other errors - return 502 with safe message
        raise HTTPException(status_code=502, detail="Notion query failed")
```

### Added: debug endpoint (after line 99)

```python
@router.get("/debug")
def debug_tasks() -> dict:
    """
    Debug endpoint to check Notion configuration and available status values.
    Does not expose secrets.
    """
    try:
        configured = bool(NOTION_PUBLIC_TASKS_DB_ID)
        status_values = []
        
        if configured:
            try:
                c = _client()
                is_status_type, status_mapping = _get_status_mapping(c)
                status_values = sorted(status_mapping.values())
            except Exception:
                pass  # Don't fail if we can't fetch
        
        return {
            "db": NOTION_PUBLIC_TASKS_DB_ID if configured else None,
            "configured": configured,
            "statusValues": status_values,
        }
    except Exception:
        return {
            "db": None,
            "configured": False,
            "statusValues": [],
        }
```

---

## File: apps/miniapp-web/src/components/TaskCard.tsx

### Modified: Scope/Done display (lines 15-20)

**Before:**
```tsx
      <div className="mt-3 text-xs text-gray-500">
        {(t.scope ?? null) != null && (t.done ?? null) != null ? (
          <span>Scope {t.done}/{t.scope}</span>
        ) : null}
        <span className="ml-2">Updated {new Date(t.lastUpdated).toLocaleString()}</span>
      </div>
```

**After:**
```tsx
      <div className="mt-3 text-xs text-gray-500">
        {((t.scope ?? null) != null || (t.done ?? null) != null) && (
          <span>
            {(t.scope ?? null) != null && (t.done ?? null) != null ? (
              <>Scope {t.scope} • Done {t.done}</>
            ) : (t.scope ?? null) != null ? (
              <>Scope {t.scope}</>
            ) : (
              <>Done {t.done}</>
            )}
          </span>
        )}
        {t.lastUpdated && (
          <span className={((t.scope ?? null) != null || (t.done ?? null) != null) ? "ml-2" : ""}>
            Updated {new Date(t.lastUpdated).toLocaleDateString(undefined, { 
              month: 'short', 
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
        )}
      </div>
```

### Modified: Progress bar (lines 21-23)

**Before:**
```tsx
      <div className="mt-3 h-2 w-full rounded bg-gray-200 overflow-hidden">
        <div style={{ width: `${pct}%` }} className="h-full rounded bg-black" />
      </div>
```

**After:**
```tsx
      <div className="mt-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-600">Progress</span>
          <span className="text-xs font-medium text-gray-700">{pct}%</span>
        </div>
        <div className="h-2 w-full rounded bg-gray-200 overflow-hidden">
          <div style={{ width: `${pct}%` }} className="h-full rounded bg-black" />
        </div>
      </div>
```

---

## File: apps/miniapp-web/src/components/TasksModal.tsx

### Modified: Loading and error states (lines 36-37)

**Before:**
```tsx
        {!items && !err && <div className="mt-6 text-sm text-gray-500">Loading…</div>}
        {err && <div className="mt-6 text-sm text-red-600">{err}</div>}
```

**After:**
```tsx
        {!items && !err && (
          <div className="mt-6 space-y-2">
            <div className="h-4 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2" />
          </div>
        )}
        {err && (
          <div className="mt-6 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="text-sm font-medium text-red-800">Can't reach Notion right now</div>
            <div className="text-xs text-red-600 mt-1">Please try again later.</div>
          </div>
        )}
```

