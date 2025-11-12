# CSV Skills End-to-End Fix Changelog

## Summary
Fixed CSV skills loading end-to-end: compose mount, robust CSV reader, stable DTO, and debug route. Ensures `/api/skills` returns non-empty list and `/api/skills/{slug}` returns details when `SKILLS_SOURCE=csv`.

## Changes

### 1. Docker Compose Override Fix (`infra/compose/miniapp.csv.override.yml`)
- **Issue**: Mounting file directly (`skills.csv:/app/data/skills.csv`) caused "mount directory onto file" error
- **Fix**: Changed to mount directory (`../../apps/miniapp-api/data:/app/data:ro`)
- **Result**: CSV file is now properly accessible at `/app/data/skills.csv` inside container

### 2. Robust CSV Reader (`apps/miniapp-api/app/services/skills_loader.py`)
- **Issue**: `csv.DictReader` failed on quoted multiline cells (e.g., "Expected 10 fields in line 3, saw 13")
- **Fix**: Replaced with `pandas.read_csv()` using Python engine for robust handling of:
  - Quoted multiline cells
  - Literal `\n` sequences
  - UTF-8 BOM encoding
  - Malformed lines (skipped instead of failing)
- **Changes**:
  - Added `pandas` import at module level
  - Updated `_load_csv()` to use `pd.read_csv()` with `engine="python"`
  - Added compatibility handling for pandas versions (supports both `on_bad_lines` and `error_bad_lines`)
  - Improved error logging with `skills_csv_read_failed` prefix
  - Normalized column names to lowercase for case-insensitive matching
  - Handle NaN values properly when converting to strings

### 3. Debug Route Enhancement (`apps/miniapp-api/routers/skills.py`)
- **Issue**: Debug route existed but didn't show `csv_ok` status or errors
- **Fix**: Enhanced `/api/skills/debug` endpoint to return:
  - `source`: "csv", "fallback", or "unknown"
  - `count`: Number of skills loaded
  - `csv_path`: Path to CSV file
  - `csv_exists`: Whether file exists
  - `csv_ok`: Whether CSV loaded successfully (new)
  - `errors`: List of error messages if any (new)
  - `sample`: Sample skills for verification
- **Note**: Route is already correctly ordered before `/{slug}` route

### 4. Fallback Policy Enforcement
- **Issue**: When `SKILLS_SOURCE=csv`, system should never call Notion, even if CSV fails
- **Fix**: 
  - `_load_skills_with_fallback()` already ensures CSV-only mode
  - When CSV fails, returns static fallback (2-3 items) instead of empty list
  - `SkillsRepository._load_snapshot()` already respects `SKILLS_SOURCE=csv` and never calls Notion
- **Result**: UI never goes empty when `SKILLS_SOURCE=csv`

## API Contract

### GET `/api/skills?lang=ru|en`
Returns: `[{ slug, title, short, tags }]`
- Always returns non-empty array (from CSV or fallback)
- Language-specific fields based on `lang` parameter

### GET `/api/skills/{slug}?lang=ru|en`
Returns: `{ slug, title, short, tags, bullets:[], examples:[] }`
- Returns 404 if skill not found
- Language-specific fields based on `lang` parameter

### GET `/api/skills/debug`
Returns: `{ source, count, csv_path, csv_exists, csv_ok, errors?, sample }`
- Shows diagnostics without leaking secrets
- `csv_ok` indicates if CSV loaded successfully
- `errors` array contains any error messages
- `source` shows actual source used ("csv" or "fallback")

## Testing

### Docker Compose Config Validation
```bash
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml config \
  | sed -n '/services:/,/volumes:/p' | sed -n '/api:/,/^[^ ]/p'
```

Expected:
- `environment.SKILLS_SOURCE: csv`
- `environment.SKILLS_CSV_PATH: /app/data/skills.csv`
- `volumes: ../../apps/miniapp-api/data:/app/data:ro`

### Container Verification
```bash
# Inside container
printenv | egrep '^(SKILLS_SOURCE|SKILLS_CSV_PATH|NOTION_)' || true
ls -l ${SKILLS_CSV_PATH:-/app/data/skills.csv}
head -n2 ${SKILLS_CSV_PATH:-/app/data/skills.csv} | nl -ba
```

### API Endpoints
```bash
# List skills
curl -sS "$ORIGIN/api/skills?lang=en" | jq 'length'
curl -sS "$ORIGIN/api/skills?lang=ru" | jq 'length'
curl -sS "$ORIGIN/api/skills?lang=en" | jq '.[0]'

# Debug endpoint
curl -sS "$ORIGIN/api/skills/debug" | jq .
```

Expected:
- `length > 0` for list endpoints
- Debug shows `source: "csv"` (or "fallback" if CSV failed)
- Debug shows `csv_ok: true` if CSV loaded successfully
- Debug shows `count > 0`

## Files Modified

1. `infra/compose/miniapp.csv.override.yml` - Fixed volume mount
2. `apps/miniapp-api/app/services/skills_loader.py` - Robust CSV parsing with pandas
3. `apps/miniapp-api/routers/skills.py` - Enhanced debug route

## Dependencies

- `pandas==2.2.2` (already in requirements.txt)

## Notes

- No breaking changes to API contract
- Frontend requires no changes (uses existing `/api/skills` endpoints)
- CSV file must be UTF-8 encoded (with or without BOM)
- CSV headers are case-insensitive (normalized to lowercase)
- Fallback skills are hardcoded in `skills_fallback.py` (2 items)

