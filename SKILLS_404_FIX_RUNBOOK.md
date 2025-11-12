# Skills 404 Fix — Runbook

## Quick Verification Commands

### 1. Backend Routes Introspection

```bash
# Check FastAPI routes (from api container)
docker compose exec -T api python -c "
from apps.miniapp_api.main import app
routes = sorted(set([r.path for r in app.routes if 'skills' in r.path]))
print('Skills routes:')
for r in routes:
    print(f'  {r}')
"
```

Expected output:
```
Skills routes:
  /api/skills
  /api/skills/debug
  /api/skills/{slug}
  /api/skills/ask
  /skills
  /rules
  /rules/{slug}
```

### 2. Direct Backend Check (from web container)

```bash
# Test API connectivity
docker compose exec -T web wget -S -O- http://api:8000/api/skills?lang=en 2>&1 | head -20
```

Expected: `HTTP/1.1 200 OK` and JSON response.

### 3. Production Host Check

```bash
# Check list endpoint
curl -i "https://miniapp.dmitrybond.tech/api/skills?lang=en" | egrep -i '^(HTTP/|content-type:)'

# Check detail endpoint
curl -s "https://miniapp.dmitrybond.tech/api/skills/automation?lang=en" | jq '{slug,title,bullets: .bullets[0:2], examples: .examples[0:2]}'
```

Expected: `HTTP/1.1 200 OK` and valid JSON.

### 4. Frontend Browser Console Check

Open browser DevTools Console on `/en/skills?lang=en` and run:

```javascript
import('/src/shared/api.ts').then(m => {
  console.log('getApiBaseUrl()', m.getApiBaseUrl?.());
  console.log('apiUrl("/skills"):', m.apiUrl?.('/skills'));
  console.log('apiUrl("/api/skills"):', m.apiUrl?.('/api/skills'));
});
```

Expected output:
- `getApiBaseUrl()` → `"/api"`
- `apiUrl("/skills")` → `"/api/skills"`
- `apiUrl("/api/skills")` → `"/api/api/skills"` (demonstrates double prefix issue)

### 5. Network Tab Verification

1. Open `/en/skills?lang=en` in browser
2. Open DevTools → Network tab
3. Reload page
4. Filter by "skills"
5. Verify requests:
   - ✅ `GET /api/skills?lang=en` → 200 OK
   - ✅ `GET /api/skills/{slug}?lang=en` → 200 OK (when opening modal)
   - ❌ NOT `skills?lang=en` (relative path)
   - ❌ NOT `/api/api/skills` (double prefix)

### 6. CSV Source Verification

```bash
docker compose exec -T api sh -lc '
  echo "SKILLS_SOURCE=$SKILLS_SOURCE";
  echo "SKILLS_CSV_PATH=$SKILLS_CSV_PATH";
  ls -l $SKILLS_CSV_PATH 2>/dev/null || echo "CSV path not set or file missing";
  head -n2 ${SKILLS_CSV_PATH:-/app/data/skills.csv} 2>/dev/null || echo "Cannot read CSV"
'
```

Expected:
- `SKILLS_SOURCE=csv` (or `auto`)
- CSV file exists and has headers: `Title EN,Bullets EN,...`

### 7. Skills Page Visual Check

1. Navigate to `/en/skills?lang=en`
2. Verify:
   - ✅ Grid of skill cards renders
   - ✅ Clicking a card opens modal with 60px top offset
   - ✅ Modal shows skill details (title, bullets, examples)
   - ✅ No 404 errors in console
   - ✅ No network errors

## Troubleshooting

### If still getting 404:

1. **Check API base URL**:
   ```javascript
   // In browser console
   console.log(window.__API_BASE__); // Should be undefined or "/api"
   console.log(import.meta.env.VITE_API_BASE_URL); // Should be undefined or "/api"
   ```

2. **Check build**:
   ```bash
   # Rebuild frontend
   docker compose build web
   docker compose up -d web
   ```

3. **Check backend logs**:
   ```bash
   docker compose logs api | grep -i skills
   ```

### If CSV not loading:

1. Check environment:
   ```bash
   docker compose exec -T api env | grep SKILLS
   ```

2. Verify CSV file:
   ```bash
   docker compose exec -T api cat /app/data/skills.csv | head -5
   ```

3. Check debug endpoint:
   ```bash
   curl -s "https://miniapp.dmitrybond.tech/api/skills/debug" | jq
   ```

