# CSV Skills Restore — Unified Diff Summary

## File: `apps/miniapp-api/app/services/skills_loader.py`

### Changes to `_load_csv()` method

**Lines 204-232:** Enhanced CSV reading with better error handling

```python
# Added keep_default_na=False to prevent empty strings from being treated as NaN
read_kwargs = {
    "encoding": enc,
    "engine": "python",
    "quotechar": '"',
    "skipinitialspace": True,
    "keep_default_na": False,  # NEW: Don't treat empty strings as NaN
}

# Enhanced fallback for older pandas versions (triple fallback)
try:
    df = pd.read_csv(csv_path, **read_kwargs, on_bad_lines="skip")
except TypeError:
    try:
        df = pd.read_csv(csv_path, **read_kwargs, error_bad_lines=False, warn_bad_lines=False)
    except TypeError:
        # Even older pandas - remove keep_default_na if not supported
        read_kwargs.pop("keep_default_na", None)
        df = pd.read_csv(csv_path, **read_kwargs, error_bad_lines=False, warn_bad_lines=False)
```

**Lines 244-252:** Improved NaN/None handling in row processing

```python
# BEFORE:
row_str = {str(k).lower(): (str(v) if pd.notna(v) else "") for k, v in row.items()}

# AFTER:
row_str = {}
for k, v in row.items():
    key_lower = str(k).lower()
    if pd.isna(v) or v is None:
        row_str[key_lower] = ""
    else:
        row_str[key_lower] = str(v)
```

### Changes to `_resolve_csv_path()` method

**Lines 173-179:** Simplified path resolution

```python
# BEFORE:
def _resolve_csv_path(self) -> Path:
    csv_path_env = os.getenv("SKILLS_CSV_PATH")
    if csv_path_env:
        return Path(csv_path_env)
    default_csv = Path(__file__).resolve().parent.parent.parent / "data" / "skills.csv"
    return Path(os.getenv("SKILLS_CSV_PATH") or "/app/data/skills.csv" or str(default_csv))

# AFTER:
def _resolve_csv_path(self) -> Path:
    csv_path_env = os.getenv("SKILLS_CSV_PATH")
    if csv_path_env:
        return Path(csv_path_env)
    # Default to /app/data/skills.csv (container path)
    return Path("/app/data/skills.csv")
```

## File: `tools/validate_skills_csv.py`

### New file created

```python
#!/usr/bin/env python3
"""Validate skills CSV file structure and content.

Checks:
- Header has exactly 10 columns
- Every quoted field is properly closed
- Reports first broken line index
"""
# ... (full implementation)
```

**Features:**
- Validates CSV header (10 columns)
- Checks each row has correct field count
- Validates UTF-8 encoding
- Optional pandas-based validation for multiline quoted fields
- Clear error reporting

## File: `Makefile`

### Added `validate-csv` target

```makefile
.PHONY: pull up down logs ps config validate-csv

# ... existing targets ...

validate-csv:
	python3 tools/validate_skills_csv.py
```

## File: `infra/compose/miniapp.csv.override.yml`

### Verified (no changes needed)

```yaml
services:
  api:
    environment:
      SKILLS_SOURCE: ${SKILLS_SOURCE:-csv}
      SKILLS_CSV_PATH: ${SKILLS_CSV_PATH:-/app/data/skills.csv}
    volumes:
      - ../../apps/miniapp-api/data:/app/data:ro
```

**Status:** Configuration is correct - directory mount (not file mount), proper environment variables.

## File: `apps/miniapp-api/routers/skills.py`

### Verified (no changes needed)

**Router order is correct:**
- Line 164: `@api_router.get("/skills")` - list endpoint
- Line 172: `@api_router.get("/skills/debug")` - debug endpoint (before slug route)
- Line 252: `@api_router.get("/skills/{slug}")` - detail endpoint

**CSV mode handling verified:**
- `_load_skills_with_fallback()` never calls Notion when `SKILLS_SOURCE=csv`
- Fallback skills used when CSV fails or returns 0 skills
- All endpoints (`/skills`, `/skills/{slug}`, `/skills/search`, `/skills/ask`) properly check `SKILLS_SOURCE`

## Summary of Changes

1. **CSV Loader Robustness**
   - Added `keep_default_na=False` for better empty string handling
   - Enhanced error handling with triple fallback for pandas compatibility
   - Improved NaN/None value conversion
   - Simplified path resolution

2. **CSV Validation Tool**
   - New validation script for early error detection
   - Makefile integration for easy access
   - UTF-8 encoding validation
   - Field count validation

3. **Configuration Verification**
   - Compose override verified correct
   - Router order verified correct
   - CSV mode isolation verified (no Notion calls)

## Testing

All changes maintain backward compatibility. The CSV loader improvements make parsing more robust without changing the API contract.

**Validation:**
```bash
# Validate CSV format
make validate-csv
# Output: [OK] CSV file is valid: apps\miniapp-api\data\skills.csv
```

## Impact

- ✅ More robust CSV parsing (handles edge cases better)
- ✅ Better error messages and diagnostics
- ✅ Early validation of CSV format issues
- ✅ No breaking changes to API contract
- ✅ Maintains backward compatibility

