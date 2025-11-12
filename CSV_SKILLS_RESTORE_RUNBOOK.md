# CSV Skills Restore — Runbook

## Prerequisites

- Docker Compose installed
- Access to `/srv/ai-avatar/infra/compose` directory (or equivalent)
- CSV file exists at `apps/miniapp-api/data/skills.csv`

## Step 1: Verify Compose Configuration

Check that the compose override has correct environment and volume settings:

```bash
cd /srv/ai-avatar/infra/compose

docker compose \
  -f miniapp.compose.yaml \
  -f miniapp.runtime.yml \
  -f miniapp.stack.yml \
  -f miniapp.csv.override.yml \
  config | grep -A 20 "api:"
```

**Expected output should show:**
- `SKILLS_SOURCE: csv`
- `SKILLS_CSV_PATH: /app/data/skills.csv`
- Volume mount: `../../apps/miniapp-api/data:/app/data:ro`

## Step 2: Verify CSV File Exists

```bash
# On host
ls -l apps/miniapp-api/data/skills.csv

# Should show file exists and is readable
```

## Step 3: Validate CSV Format (Optional)

```bash
# From project root
make validate-csv

# Or directly:
python3 tools/validate_skills_csv.py apps/miniapp-api/data/skills.csv
```

**Expected:** `✓ CSV file is valid`

## Step 4: Check Container Environment

```bash
cd /srv/ai-avatar/infra/compose

docker compose \
  -f miniapp.compose.yaml \
  -f miniapp.runtime.yml \
  -f miniapp.stack.yml \
  -f miniapp.csv.override.yml \
  exec -T api sh -lc '
    echo "[env]"
    for k in SKILLS_SOURCE SKILLS_CSV_PATH NOTION_API_KEY NOTION_DB_SKILLS; do
      v=$(eval echo \$$k)
      if [ -n "$v" ]; then
        echo "$k=SET(len:${#v})"
      else
        echo "$k=<EMPTY>"
      fi
    done
    echo "[csv]"
    ls -l "${SKILLS_CSV_PATH:-/app/data/skills.csv}" || true
    echo "[head]"
    head -n2 "${SKILLS_CSV_PATH:-/app/data/skills.csv}" | nl -ba
  '
```

**Expected:**
- `SKILLS_SOURCE=SET(len:3)` (value: "csv")
- `SKILLS_CSV_PATH=SET(len:20)` (value: "/app/data/skills.csv")
- `NOTION_API_KEY=<EMPTY>` (should be empty in CSV mode)
- CSV file exists and is readable
- First 2 lines of CSV shown

## Step 5: Test API Endpoints

Set `ORIGIN` to your API base URL (e.g., `http://localhost:8000` or production URL):

```bash
export ORIGIN="http://localhost:8000"  # Adjust as needed

# Test list endpoint (English)
curl -sS "$ORIGIN/api/skills?lang=en" | jq 'length'
# Expected: > 0

# Test list endpoint (Russian)
curl -sS "$ORIGIN/api/skills?lang=ru" | jq 'length'
# Expected: > 0

# Test detail endpoint
curl -sS "$ORIGIN/api/skills/automation?lang=en" | jq '.bullets | length'
# Expected: > 0

# Test debug endpoint
curl -sS "$ORIGIN/api/skills/debug" | jq .
# Expected: {
#   "source": "csv",
#   "count": <number>,
#   "csv_path": "/app/data/skills.csv",
#   "csv_exists": true,
#   "csv_ok": true,
#   "errors": null,
#   "sample": [...]
# }
```

## Step 6: Verify No Notion Calls

```bash
# Check API logs for Notion calls
docker compose \
  -f miniapp.compose.yaml \
  -f miniapp.runtime.yml \
  -f miniapp.stack.yml \
  -f miniapp.csv.override.yml \
  logs api | grep -i notion

# Expected: No matches (or only initialization logs, not API calls)
```

## Step 7: Test Fallback Behavior

To test fallback, temporarily rename or remove CSV file:

```bash
# Backup CSV
mv apps/miniapp-api/data/skills.csv apps/miniapp-api/data/skills.csv.bak

# Restart API service
docker compose \
  -f miniapp.compose.yaml \
  -f miniapp.runtime.yml \
  -f miniapp.stack.yml \
  -f miniapp.csv.override.yml \
  restart api

# Wait a few seconds, then test
sleep 5
curl -sS "$ORIGIN/api/skills?lang=en" | jq 'length'
# Expected: 2 (fallback skills)

curl -sS "$ORIGIN/api/skills/debug" | jq '.source'
# Expected: "fallback"

# Restore CSV
mv apps/miniapp-api/data/skills.csv.bak apps/miniapp-api/data/skills.csv
docker compose ... restart api
```

## Step 8: Frontend Verification

1. Open frontend in browser
2. Navigate to skills page
3. Verify skills tiles are displayed (not "No skills are published yet")
4. Click on a skill to verify detail view shows bullets and examples
5. Check browser DevTools Network tab:
   - Request to `/api/skills?lang=...` returns 200
   - Response contains non-empty array
   - No network errors

## Troubleshooting

### Issue: API returns empty array `[]`

**Check:**
1. CSV file exists and is readable in container
2. `SKILLS_SOURCE=csv` is set
3. CSV file has correct format (10 columns)
4. Check API logs for CSV parsing errors

**Fix:**
```bash
# Check CSV in container
docker compose ... exec api cat /app/data/skills.csv | head -n 3

# Validate CSV format
make validate-csv

# Check API logs
docker compose ... logs api | grep -i csv
```

### Issue: "Are you trying to mount a directory onto a file" error

**Cause:** Compose override has incorrect volume mount (file instead of directory)

**Fix:** Ensure `miniapp.csv.override.yml` has:
```yaml
volumes:
  - ../../apps/miniapp-api/data:/app/data:ro
```
Not:
```yaml
volumes:
  - ../../apps/miniapp-api/data/skills.csv:/app/data/skills.csv:ro
```

### Issue: CSV parsing errors in logs

**Check:**
1. CSV file encoding (should be UTF-8)
2. All quoted fields are properly closed
3. No extra commas in unquoted fields
4. Header matches expected format

**Fix:**
```bash
# Validate CSV
make validate-csv

# Check for encoding issues
file -bi apps/miniapp-api/data/skills.csv
# Should show: text/plain; charset=utf-8
```

### Issue: Debug endpoint shows `csv_ok: false`

**Check:**
1. CSV file exists at path shown in `csv_path`
2. CSV file is readable (permissions)
3. CSV file has correct format

**Fix:**
```bash
# Check file in container
docker compose ... exec api ls -l /app/data/skills.csv

# Check file content
docker compose ... exec api head -n 5 /app/data/skills.csv

# Validate format
make validate-csv
```

## Acceptance Criteria

✅ `docker compose config` shows `SKILLS_SOURCE=csv` and directory mount  
✅ `/api/skills?lang=...` returns non-empty array  
✅ `/api/skills/{slug}?lang=...` returns detail object with bullets/examples  
✅ `/api/skills/debug` returns `{ source: "csv", count > 0, csv_ok: true }`  
✅ Zero Notion calls in logs when `SKILLS_SOURCE=csv`  
✅ Frontend tiles render correctly without code/UX changes  

## Rollback

If issues occur, remove CSV override:

```bash
docker compose \
  -f miniapp.compose.yaml \
  -f miniapp.runtime.yml \
  -f miniapp.stack.yml \
  up -d api
```

This will use default configuration (likely Notion or auto mode).

