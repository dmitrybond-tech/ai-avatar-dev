# Skills CSV Ingestion Implementation

## Summary

Implemented robust CSV ingestion for skills with tolerant header aliases and proper provider selection.

## Changes

### File: `apps/miniapp-api/app/services/skills.py`

1. **Added CSV header aliases mapping** (`CSV_ALIASES`) supporting multiple header name variations
2. **Added helper functions**:
   - `_h()`: Case-insensitive header value extraction
   - `_split_list()`: Tag splitting by `;` or `,`
   - `_split_lines()`: Bullets/examples splitting by `\n`
   - `_to_bool()`: Boolean coercion (1/true/yes/y/да)
   - `_to_int()`: Integer coercion with default fallback
3. **Replaced `_load_from_csv()`** with `_load_csv()` using standard `csv` module
4. **Updated `_load_snapshot()`** to enforce provider selection:
   - `SKILLS_SOURCE=csv` → force CSV, set `source="csv"`, `csv_fallback=True`
   - `SKILLS_SOURCE=auto` → Notion if tokens+db set, else CSV if file exists
   - `SKILLS_SOURCE=notion` → Notion only
5. **Updated `_load_from_notion()`** to return `(records, success)` tuple
6. **Added `weight` and `pinned` fields** to `SkillRecord` (defaults: 0, False)
7. **Implemented stable sorting**: pinned desc, weight desc, key asc

### File: `apps/miniapp-api/main.py`

- Updated `/api/healthz` endpoint to include `skills.source` in response

## Accepted CSV Headers & Coercions

### Header Aliases

Headers may use any alias from the `CSV_ALIASES` map. Matching is case-insensitive.

| Field | Accepted Aliases |
|-------|------------------|
| `key` | `key`, `slug`, `id` |
| `title_en` | `title_en`, `name_en`, `en_title`, `en_name`, `title` |
| `title_ru` | `title_ru`, `name_ru`, `ru_title`, `ru_name` |
| `short_en` | `short_en`, `summary_en`, `en_short`, `en_summary` |
| `short_ru` | `short_ru`, `summary_ru`, `ru_short`, `ru_summary` |
| `tags` | `tags`, `labels`, `categories` |
| `bullets_en` | `bullets_en`, `points_en`, `en_bullets` |
| `bullets_ru` | `bullets_ru`, `points_ru`, `ru_bullets` |
| `examples_en` | `examples_en`, `cases_en`, `en_examples` |
| `examples_ru` | `examples_ru`, `cases_ru`, `ru_examples` |
| `weight` | `weight`, `order`, `prio` |
| `pinned` | `pinned`, `pin`, `featured` |

### Data Coercions

- **tags**: Split by `;` or `,`; trim spaces; remove empty values
- **bullets_* / examples_***: Split by `\n`; remove leading `-`/`•`; drop empty lines
- **pinned**: Accepts `1`/`true`/`yes`/`y`/`да` (case-insensitive); defaults to `False`
- **weight**: Coerced to `int`; defaults to `0` on parse failure
- **All fields**: Values are trimmed; missing optional fields return empty strings/lists

### Required Fields

- `key` (or alias): Must be non-empty; defaults to `skill_{index}` if missing
- `title_en` or `title_ru`: At least one must be present; rows without titles are skipped

## Verification Runbook

### 1. Check CSV Provider Selection

```bash
# Set CSV source
export SKILLS_SOURCE=csv
export SKILLS_CSV_PATH=/app/data/skills.csv

# Start API (or restart if running)
# Then check debug endpoint
curl http://localhost:8000/api/skills/debug | jq
```

Expected output:
```json
{
  "provider": "csv",
  "csv_path": "/app/data/skills.csv",
  "csv_exists": true,
  "count": 5,
  "sample": [...]
}
```

### 2. Verify Skills List Endpoint

```bash
# Russian
curl "http://localhost:8000/api/skills?lang=ru" | jq '.[0]'

# English
curl "http://localhost:8000/api/skills?lang=en" | jq '.[0]'
```

Expected: First item has `slug`, `title`, `short`, `tags` keys.

### 3. Verify Skills Detail Endpoint

```bash
# Get first skill slug
SLUG=$(curl -s "http://localhost:8000/api/skills?lang=ru" | jq -r '.[0].slug')

# Get detail
curl "http://localhost:8000/api/skills/${SLUG}?lang=en" | jq
```

Expected: Response includes `bullets` and `examples` arrays.

### 4. Verify Healthz Endpoint

```bash
curl http://localhost:8000/api/healthz | jq
```

Expected:
```json
{
  "ok": true,
  "skills": {
    "source": "csv"
  }
}
```

### 5. Test Auto Mode

```bash
# Without Notion credentials
unset NOTION_API_KEY
unset NOTION_DB_SKILLS
export SKILLS_SOURCE=auto

# Restart API, then check
curl http://localhost:8000/api/skills/debug | jq '.provider'
# Should return "csv"
```

### 6. Test CSV Header Tolerance

Create a test CSV with alternate headers:
```csv
Slug,Title EN,Title RU,Tags,Weight,Pinned
test-skill,Test EN,Test RU,"tag1, tag2",10,1
```

Verify it loads correctly:
```bash
export SKILLS_CSV_PATH=/path/to/test.csv
export SKILLS_SOURCE=csv
# Restart API
curl "http://localhost:8000/api/skills?lang=en" | jq '.[] | select(.slug=="test-skill")'
```

## Notes

- CSV parsing uses standard `csv` module (no pandas dependency for CSV loading)
- Header matching is case-insensitive
- Empty rows are skipped
- Skills are sorted: pinned first, then by weight desc, then by key asc
- Provider selection respects `SKILLS_SOURCE` environment variable
- Debug endpoint shows provider, CSV path, existence, and sample data

