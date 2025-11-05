# Notion Public Tasks Integration - Changelog

## Summary

This implementation adds a robust Notion integration for the AI-Avatar mini-app to manage "Public On-Board Tasks" with full CRUD operations, progress tracking, and public JSON API endpoints.

## Dependencies

### Added
- `notion-client==2.2.4` - Official Notion API client library (Python 3.11+ compatible)
- `pytest==8.3.4` - Testing framework for unit tests

## Files Created

### Backend Integration Module
1. **apps/api/src/app/integrations/__init__.py**
   - Package initialization for integrations module

2. **apps/api/src/app/integrations/notion_public_tasks.py** (472 lines)
   - Notion client initialization with timeout support
   - Mapping constants for status values and property names
   - Pydantic models: `PublicTaskIn`, `PublicTaskOut`, `PublicTaskUpdate`, `PublicTaskCreate`
   - CRUD functions:
     - `query_public_tasks()` - Query public tasks with filtering and sorting
     - `create_task()` - Create new tasks with defaults
     - `update_task()` - Update tasks with automatic progress computation
     - `add_comment()` - Add internal comments to tasks
   - `assert_schema()` - Database schema validation
   - `compute_progress()` - Progress percentage calculation (round(100*Done/max(Scope,1)))

### API Router
3. **apps/api/src/app/adapters/web/public_tasks.py** (152 lines)
   - FastAPI router with prefix `/api/tasks`
   - Endpoints:
     - `GET /api/tasks/public` - List public tasks (read-only, no auth required)
     - `POST /api/tasks` - Create task (auth optional for mini-app)
     - `PATCH /api/tasks/{id}` - Update task (auth required)
     - `POST /api/tasks/{id}/comment` - Add comment (auth required)
   - Bearer token authentication using JWT_SECRET
   - Input validation and length limits

### API Schemas
4. **apps/api/src/app/schemas/public_tasks.py** (65 lines)
   - Pydantic models for API request/response:
     - `PublicTaskOut` - Public task listing response
     - `PublicTaskCreate` - Task creation request
     - `PublicTaskUpdate` - Task update request
     - `CommentRequest` - Comment creation request
   - Validation for status values and source values

### Tests
5. **apps/api/tests/__init__.py**
   - Test package initialization

6. **apps/api/tests/test_notion_public_tasks.py** (345 lines)
   - Comprehensive unit tests with mocked Notion API calls
   - Test coverage:
     - Progress computation logic (zero scope, normal, complete, over 100%, negative)
     - Query public tasks (success, no DB ID, API errors)
     - Create task (success, with progress)
     - Update task (status, progress)
     - Add comment (success, truncated text)
     - Schema assertion (success, missing property, wrong type)

## Files Modified

### Backend Core
1. **apps/api/src/app/core/settings.py**
   - Added Notion configuration settings:
     - `notion_api_key: str` - Notion Integration Secret (env: `NOTION_API_KEY`)
     - `notion_public_tasks_db_id: str` - Database ID (env: `NOTION_PUBLIC_TASKS_DB_ID`)
     - `notion_timeout: int = 10` - API timeout in seconds (env: `NOTION_TIMEOUT`)

2. **apps/api/src/app/main.py**
   - Added import for `public_tasks` router and `assert_schema`
   - Wired `public_tasks.router` into FastAPI app
   - Added schema assertion check in startup lifespan (logs warning if schema mismatch)

### Dependencies
3. **apps/api/requirements.txt**
   - Added `notion-client==2.2.4`
   - Added `pytest==8.3.4`

### Infrastructure
4. **infra/compose/miniapp.compose.yaml**
   - Added Notion environment variables to API service:
     - `NOTION_API_KEY=${NOTION_API_KEY:-}`
     - `NOTION_PUBLIC_TASKS_DB_ID=${NOTION_PUBLIC_TASKS_DB_ID:-}`
     - `NOTION_TIMEOUT=${NOTION_TIMEOUT:-10}`

5. **infra/compose/env.example**
   - Added Notion Integration section:
     - `NOTION_API_KEY=`
     - `NOTION_PUBLIC_TASKS_DB_ID=`
     - `NOTION_TIMEOUT=10`

## Numbered Change Log

1. **Dependency Management**
   - Added `notion-client==2.2.4` to `apps/api/requirements.txt`
   - Added `pytest==8.3.4` to `apps/api/requirements.txt` for testing

2. **Settings Configuration**
   - Added `notion_api_key`, `notion_public_tasks_db_id`, and `notion_timeout` to `Settings` class in `apps/api/src/app/core/settings.py`

3. **Integration Module**
   - Created `apps/api/src/app/integrations/` directory
   - Implemented `notion_public_tasks.py` with:
     - Notion client singleton pattern
     - Property name constants matching Notion DB schema
     - Status and source value mappings
     - Pydantic models for data validation
     - CRUD operations with error handling
     - Progress computation logic
     - Schema assertion function

4. **API Router**
   - Created `apps/api/src/app/adapters/web/public_tasks.py` router
   - Implemented 4 REST endpoints:
     - Public listing (no auth)
     - Task creation (optional auth)
     - Task updates (required auth)
     - Comment addition (required auth)
   - Added input validation and length limits
   - Implemented Bearer token authentication

5. **API Schemas**
   - Created `apps/api/src/app/schemas/public_tasks.py`
   - Defined Pydantic models for API contracts
   - Added field validators for status and source values

6. **Main Application**
   - Wired `public_tasks` router into FastAPI app in `apps/api/src/app/main.py`
   - Added schema assertion check in application lifespan
   - Logs warning on schema mismatch (non-blocking)

7. **Testing**
   - Created `apps/api/tests/` directory
   - Implemented comprehensive unit tests with mocked Notion API
   - Test coverage includes all CRUD operations and edge cases

8. **Infrastructure**
   - Updated `infra/compose/miniapp.compose.yaml` to pass Notion env vars to API service
   - Updated `infra/compose/env.example` with Notion configuration template

## Environment Variables

The following environment variables must be set:

- `NOTION_API_KEY` - Notion Integration Secret (from https://www.notion.so/my-integrations)
- `NOTION_PUBLIC_TASKS_DB_ID` - Database ID for "Public On-Board Tasks" database
- `NOTION_TIMEOUT` - Optional, defaults to 10 seconds

## Notion Database Schema Requirements

The Notion database must have the following properties:

| Property Name | Type | Required | Description |
|--------------|------|----------|-------------|
| Name | Title | Yes | Task title |
| Status | Select | Yes | Status options: Backlog, In Progress, Review, Blocked, Done |
| Public? | Checkbox | Yes | Marks task as public |
| Scope | Number | Yes | Total scope/effort |
| Done | Number | Yes | Completed scope/effort |
| Progress % | Number | Yes | Auto-computed percentage (0-100) |
| Review At | Date | No | Review deadline |
| Tags | Multi-select | No | Task tags |
| Source | Select | No | Source values: MiniApp, Bot, Manual |
| Last Updated | Formula | No | Formula referencing `last_edited_time` (for sorting) |

## API Endpoints

### GET /api/tasks/public
- **Description**: List public tasks
- **Auth**: None required
- **Query Parameters**: `limit` (default: 100, max: 1000)
- **Response**: Array of `PublicTaskOut` objects

### POST /api/tasks
- **Description**: Create a new task
- **Auth**: Optional (Bearer token)
- **Request Body**: `PublicTaskCreate`
- **Response**: `PublicTaskOut` with created task

### PATCH /api/tasks/{id}
- **Description**: Update an existing task
- **Auth**: Required (Bearer token)
- **Request Body**: `PublicTaskUpdate` (partial)
- **Response**: `PublicTaskOut` with updated task
- **Note**: Automatically recomputes Progress % when Scope or Done changes

### POST /api/tasks/{id}/comment
- **Description**: Add internal comment to task
- **Auth**: Required (Bearer token)
- **Request Body**: `CommentRequest`
- **Response**: `{"status": "ok", "message": "Comment added"}`

## Data Contracts

### PublicTaskOut
```json
{
  "id": "string (Notion page id)",
  "title": "string",
  "status": "Backlog|In Progress|Review|Blocked|Done",
  "progressPct": 0..100,
  "reviewAt": "ISO 8601 or null",
  "lastUpdated": "ISO 8601",
  "tags": ["..."],
  "url": "https://notion.so/..."
}
```

## Security Features

- Bearer token authentication for protected endpoints
- Input length validation (title: 200 chars, comment: 1000 chars)
- Input sanitization
- Error logging with Notion API request IDs
- No secrets leaked in logs

## Testing

Run tests with:
```bash
cd apps/api
pytest tests/test_notion_public_tasks.py -v
```

Test coverage includes:
- Progress computation edge cases
- CRUD operations success and failure paths
- Schema validation
- API error handling
- Input validation

## Notes

- Schema assertion runs on application startup and logs a warning (non-blocking) if schema mismatch is detected
- Progress percentage is automatically computed as `round(100 * Done / max(Scope, 1))` and capped at 100%
- Comments are internal and not exposed in public listings
- Public listing excludes internal fields and comments
- Notion page URLs are generated as `https://notion.so/{page_id_without_dashes}`

## Future Enhancements (Not Implemented)

- Rate limiting per IP/token for creation endpoint
- Frontend integration hooks in mini-app (mentioned as optional)
- Enhanced authentication with existing project auth scheme

