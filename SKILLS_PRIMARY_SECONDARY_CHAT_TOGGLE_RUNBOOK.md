# Skills Primary/Secondary + Chat Toggle Wiring - Runbook

## Prerequisites

- Docker Compose with `.env.miniapp` configured
- `SKILLS_SOURCE=csv` (or `auto` with CSV fallback)
- `SKILLS_CSV_PATH=/app/data/skills.csv` (or custom path)
- CSV file present at configured path
- Backend API running on port 8000 (or configured port)

---

## Backend Verification

### 1. Check CSV Configuration

**Bash:**
```bash
docker compose --env-file .env.miniapp \
  -f infra/compose/miniapp.compose.yaml \
  -f infra/compose/miniapp.runtime.yml \
  -f infra/compose/miniapp.stack.yml \
  -f infra/compose/miniapp.csv.override.yml \
  -f infra/compose/miniapp.llm.override.yml \
  exec -T api sh -lc '
    echo "SKILLS_SOURCE=$SKILLS_SOURCE";
    echo "SKILLS_CSV_PATH=$SKILLS_CSV_PATH";
    ls -l $SKILLS_CSV_PATH | head -n1
  '
```

**PowerShell:**
```powershell
docker compose --env-file .env.miniapp `
  -f infra/compose/miniapp.compose.yaml `
  -f infra/compose/miniapp.runtime.yml `
  -f infra/compose/miniapp.stack.yml `
  -f infra/compose/miniapp.csv.override.yml `
  -f infra/compose/miniapp.llm.override.yml `
  exec -T api sh -lc '
    echo "SKILLS_SOURCE=$SKILLS_SOURCE";
    echo "SKILLS_CSV_PATH=$SKILLS_CSV_PATH";
    ls -l $SKILLS_CSV_PATH | head -n1
  '
```

**Expected Output:**
```
SKILLS_SOURCE=csv
SKILLS_CSV_PATH=/app/data/skills.csv
-rw-r--r-- 1 root root 1234 Jan 15 10:00 /app/data/skills.csv
```

---

### 2. Test API Endpoints

#### GET `/api/skills?lang=ru`

**Bash:**
```bash
curl -s "https://miniapp.dmitrybond.tech/api/skills?lang=ru" | jq '.[0]'
```

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "https://miniapp.dmitrybond.tech/api/skills?lang=ru" | ConvertTo-Json -Depth 10 | Select-Object -First 20
```

**Expected Response:**
```json
{
  "slug": "automation",
  "title": "Автоматизация",
  "short": "Python ETL/ELT, миграции и связка ваших систем.",
  "tags": ["python", "etl", "elt", "migrations", "integrations"]
}
```

#### GET `/api/skills/{slug}?lang=ru`

**Bash:**
```bash
curl -s "https://miniapp.dmitrybond.tech/api/skills/automation?lang=ru" | jq '{slug,title,bullets,examples}'
```

**PowerShell:**
```powershell
$response = Invoke-RestMethod -Uri "https://miniapp.dmitrybond.tech/api/skills/automation?lang=ru"
$response | Select-Object slug, title, bullets, examples | ConvertTo-Json -Depth 10
```

**Expected Response:**
```json
{
  "slug": "automation",
  "title": "Автоматизация",
  "bullets": [
    "Проектирование ETL/ELT-пайплайнов на Python...",
    "Скрипты миграций данных и инфраструктуры...",
    ...
  ],
  "examples": [
    "Ночной импорт CSV → PostgreSQL",
    "Миграция MySQL → Aurora",
    ...
  ]
}
```

#### POST `/api/skills/ask`

**Bash:**
```bash
curl -s -X POST "https://miniapp.dmitrybond.tech/api/skills/ask" \
  -H "Content-Type: application/json" \
  -d '{"q":"Можешь ли ты автоматизировать ETL на Python?","lang":"ru"}' | jq .
```

**PowerShell:**
```powershell
$body = @{
  q = "Можешь ли ты автоматизировать ETL на Python?"
  lang = "ru"
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://miniapp.dmitrybond.tech/api/skills/ask" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 10
```

**Expected Response:**
```json
{
  "answer": "Да, я могу помочь с автоматизацией ETL на Python...",
  "used_skills": ["automation"],
  "model": "grok-beta",
  "tokens_estimate": 150
}
```

**Error Cases:**
- `401` - `XAI_API_KEY` not configured
- `502` - Grok provider unavailable
- `503` - No skills available or CSV file missing

---

### 3. Verify Router Includes

**Bash:**
```bash
docker compose --env-file .env.miniapp \
  -f infra/compose/miniapp.compose.yaml \
  exec -T api python -c "
from apps.miniapp_api.main import app
routes = [r.path for r in app.routes if 'skills' in r.path]
for r in sorted(routes):
    print(r)
"
```

**Expected Output:**
```
/api/skills
/api/skills/debug
/api/skills/ask
/api/skills/{slug}
/skills
/skills/{slug}
/rules
/rules/{slug}
```

---

## Frontend Verification

### 1. Skills Page UI

**Manual Test:**
1. Navigate to Skills page
2. Verify grid layout: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`
3. Click a skill tile
4. Verify modal opens with:
   - Top offset: 60px (check computed style: `margin-top: calc(env(safe-area-inset-top, 0px) + 60px)`)
   - Bullets section: "Что делаю" (ru) / "What I do" (en) with checkmarks (✓)
   - Examples section: "Примеры" (ru) / "Examples" (en) as cards

**Browser Console:**
```javascript
// Check adapter import
import { mapList, mapDetail } from './shared/skillsAdapter.ts';
console.log('Adapter loaded:', typeof mapList, typeof mapDetail);

// Test API call
fetch('/api/skills?lang=ru')
  .then(r => r.json())
  .then(data => console.log('Skills list:', data));
```

---

### 2. Chat Toggle Wiring

**Manual Test:**
1. Navigate to main chat screen
2. Verify checkbox "Умный ответ (LLM)" / "Smart answer (LLM)" is visible
3. Verify checkbox is NOT visible on Skills page
4. Toggle checkbox ON
5. Send message → verify network request to `/api/chat/ask_grok` or `/api/skills/ask`
6. Toggle checkbox OFF
7. Send message → verify network request to `/api/ask`

**Browser Console:**
```javascript
// Check localStorage
localStorage.getItem('SMART_LLM_ENABLED'); // "true" or "false"

// Monitor network requests
const originalFetch = window.fetch;
window.fetch = function(...args) {
  console.log('Fetch:', args[0]);
  return originalFetch.apply(this, args);
};
```

---

### 3. Error Handling

**Test Cases:**
1. **404 on skill detail:** Navigate to `/skills/nonexistent` → should show error message with retry button
2. **Network error:** Disable network → should show error message
3. **LLM unavailable:** Set `llmAvailable: false` in config → checkbox should be disabled
4. **LLM API error:** Return 502 from `/api/skills/ask` → should show user-friendly error message

---

## Troubleshooting

### Issue: `/api/skills` returns 404

**Check:**
1. Router includes in `main.py` (lines 99-101)
2. `api_router` prefix is `/api`
3. Route order: `/api/skills/debug` before `/api/skills/{slug}`

**Fix:**
```python
# In apps/miniapp-api/routers/skills.py
# Ensure debug route is BEFORE slug route
@api_router.get("/skills/debug")  # Line ~176
def debug_skills(...):
    ...

@api_router.get("/skills/{slug}")  # Line ~205
def get_skill_api(...):
    ...
```

---

### Issue: CSV not loading

**Check:**
1. `SKILLS_SOURCE=csv` in env
2. `SKILLS_CSV_PATH` points to existing file
3. File permissions (readable by container user)
4. CSV encoding (UTF-8 or UTF-8 BOM)

**Fix:**
```bash
# Check file exists
docker compose exec api ls -l /app/data/skills.csv

# Check encoding
docker compose exec api file /app/data/skills.csv

# Reload skills
docker compose exec api python -c "
from apps.miniapp_api.services.skills import SkillsRepository
repo = SkillsRepository()
repo.refresh()
print('Skills loaded:', len(repo.snapshot().skills))
"
```

---

### Issue: Modal top offset wrong

**Check:**
1. CSS class `modal-offset-mt` applied
2. CSS variable `--modal-top-offset` defined in `index.css`
3. No inline `style={{ marginTop }}` overriding

**Fix:**
```css
/* In apps/miniapp-web/src/index.css */
:root {
  --modal-top-offset: calc(env(safe-area-inset-top, 0px) + 60px);
}
```

---

### Issue: Chat toggle not working

**Check:**
1. `useSmartLLM()` hook imported and used
2. `localStorage.getItem('SMART_LLM_ENABLED')` returns correct value
3. Message submit handler checks `smartLLM` state
4. API endpoints return expected responses

**Fix:**
```typescript
// In Chat.tsx
const [smartLLM, setSmartLLM] = useSmartLLM();

// In send() function
if (smartLLM && config.llmAvailable) {
  // LLM path
} else {
  // Local path
}
```

---

## Acceptance Criteria Checklist

- [x] GET `/api/skills` returns correct data from CSV
- [x] GET `/api/skills/{slug}` returns correct detail with bullets/examples
- [x] Skills page shows primary tiles grid
- [x] Click tile → modal opens with 60px top offset
- [x] Modal shows bullets as checklist (✓)
- [x] Modal shows examples as cards
- [x] Chat toggle only on main chat screen (not Skills page)
- [x] Chat toggle ON → calls LLM endpoint
- [x] Chat toggle OFF → calls local flow
- [x] No 404/405 errors on `/api/skills/*`
- [x] LLM provider errors handled gracefully
- [x] i18n respected (ru/en)

---

## Deployment Notes

1. **Backend:** No changes needed (routers already configured)
2. **Frontend:** Build and deploy updated web app
3. **CSV:** Ensure CSV file is mounted or included in container image
4. **Env:** Set `SKILLS_SOURCE=csv` in production

---

## Rollback Plan

If issues occur:

1. **Frontend:** Revert to previous build (adapter changes are backward-compatible)
2. **Backend:** No changes made, no rollback needed
3. **CSV:** Verify CSV file exists and is readable

---

## References

- Changelog: `SKILLS_PRIMARY_SECONDARY_CHAT_TOGGLE_CHANGELOG.md`
- Unified Diff: `SKILLS_PRIMARY_SECONDARY_CHAT_TOGGLE_UNIFIED_DIFF.md`
- API Endpoints: `API_ENDPOINTS_RUNBOOK.md`

