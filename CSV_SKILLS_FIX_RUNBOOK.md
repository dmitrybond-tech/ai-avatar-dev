# CSV Skills Fix - Runbook

## Quick Reference

### Verify Docker Compose Configuration

```bash
# Check effective config for api service
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml config \
  | sed -n '/services:/,/volumes:/p' | sed -n '/api:/,/^[^ ]/p'
```

**Expected output:**
- `environment.SKILLS_SOURCE: csv`
- `environment.SKILLS_CSV_PATH: /app/data/skills.csv`
- `volumes: ../../apps/miniapp-api/data:/app/data:ro` (directory mount, not file)

### Verify Container Environment

```bash
# Enter api container
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml exec api sh

# Inside container, check environment variables
printenv | egrep '^(SKILLS_SOURCE|SKILLS_CSV_PATH|NOTION_)' || true

# Check CSV file exists and is readable
ls -l ${SKILLS_CSV_PATH:-/app/data/skills.csv}

# Preview CSV content
head -n2 ${SKILLS_CSV_PATH:-/app/data/skills.csv} | nl -ba
```

### Test API Endpoints

```bash
# Set ORIGIN variable (adjust for your environment)
export ORIGIN="http://localhost:8000"  # or your actual API URL

# Test list endpoint (English)
curl -sS "$ORIGIN/api/skills?lang=en" | jq 'length'
# Expected: number > 0

# Test list endpoint (Russian)
curl -sS "$ORIGIN/api/skills?lang=ru" | jq 'length'
# Expected: number > 0

# Test detail endpoint
curl -sS "$ORIGIN/api/skills?lang=en" | jq '.[0]'
# Expected: { slug, title, short, tags }

# Test debug endpoint
curl -sS "$ORIGIN/api/skills/debug" | jq .
# Expected: { source: "csv" | "fallback", count: > 0, csv_ok: true, csv_path: "...", csv_exists: true }
```

### Restart API Service

```bash
# Re-up only api service
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml up -d api

# Check logs
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml logs -f api
```

### Troubleshooting

#### Issue: CSV file not found
```bash
# Check if CSV file exists on host
ls -l apps/miniapp-api/data/skills.csv

# Check if directory is mounted correctly
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml exec api ls -la /app/data/
```

#### Issue: CSV parsing errors
```bash
# Check debug endpoint for errors
curl -sS "$ORIGIN/api/skills/debug" | jq '.errors'

# Check API logs for "skills_csv_read_failed"
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml logs api | grep -i "skills_csv_read_failed"
```

#### Issue: Empty skills list
```bash
# Check if fallback is being used
curl -sS "$ORIGIN/api/skills/debug" | jq '.source'
# If "fallback", CSV loading failed

# Verify CSV file encoding (should be UTF-8)
file -bi apps/miniapp-api/data/skills.csv
```

#### Issue: Notion still being called when SKILLS_SOURCE=csv
```bash
# Verify environment variable is set
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml exec api printenv SKILLS_SOURCE
# Expected: "csv"

# Check API logs for Notion calls (should be none)
docker compose -f miniapp.compose.yaml -f miniapp.runtime.yml -f miniapp.stack.yml -f miniapp.csv.override.yml logs api | grep -i notion
```

## Acceptance Criteria Checklist

- [ ] `docker compose config` shows `SKILLS_SOURCE=csv` and directory volume mount
- [ ] `/api/skills?lang=...` returns array with `length > 0`
- [ ] `/api/skills/{slug}?lang=...` returns detail object with `bullets` and `examples`
- [ ] `/api/skills/debug` exists and returns `{ source, count, csv_path, csv_ok, errors? }`
- [ ] No Notion API calls when `SKILLS_SOURCE=csv` (check logs)
- [ ] Frontend skills tiles render correctly (no code changes needed)

