# Runbook: Chat Toggle & Skills UI Fix

## Overview
This runbook provides commands to deploy and verify the chat toggle and skills UI changes.

## Prerequisites
- PowerShell (Windows) or Bash (Linux/macOS)
- Git access to repository
- Node.js and pnpm installed
- Python 3.x and virtualenv (for API)

## Deployment Steps

### 1. Verify Changes
```powershell
# PowerShell
cd C:\PersonalProjects\ai-avatar
git status
git diff apps/miniapp-web/
```

```bash
# Bash
cd /path/to/ai-avatar
git status
git diff apps/miniapp-web/
```

### 2. Build Frontend
```powershell
# PowerShell
cd apps\miniapp-web
pnpm install
pnpm build
```

```bash
# Bash
cd apps/miniapp-web
pnpm install
pnpm build
```

### 3. Verify API Endpoints (Optional)
```powershell
# PowerShell - Start API server
cd apps\miniapp-api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn apps.miniapp_api.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
# Bash - Start API server
cd apps/miniapp-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn apps.miniapp_api.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Test Locally
```powershell
# PowerShell - Start dev server
cd apps\miniapp-web
pnpm dev
```

```bash
# Bash - Start dev server
cd apps/miniapp-web
pnpm dev
```

Visit `http://localhost:5173` and verify:
1. Checkbox appears on main chat form
2. Checkbox state persists after page reload
3. Skills page has no LLM toggle
4. Skills page grid and modal work

### 5. Verify localStorage
Open browser DevTools → Application → Local Storage:
- Key: `SMART_LLM_ENABLED`
- Value: `true` or `false`
- Should persist across reloads

### 6. Test LLM Routing
1. Enable checkbox
2. Send a message
3. Check Network tab:
   - Should try `/api/chat/ask_grok` first
   - May fallback to `/api/skills/ask` if ask_grok fails
4. Verify response shows "Mode: LLM" badge

### 7. Test Fallback
Simulate ask_grok failure:
- Disable API endpoint temporarily
- Send message with checkbox enabled
- Should fallback to `/api/skills/ask`

### 8. Test Non-LLM Flow
1. Disable checkbox
2. Send a message
3. Should use `/api/ask` endpoint
4. Response shows "Mode: Skills" badge

## Verification Checklist

### Frontend
- [ ] Checkbox visible on main chat form
- [ ] Checkbox state persists in localStorage
- [ ] i18n strings display correctly (EN/RU)
- [ ] Skills page has no LLM toggle
- [ ] Skills page grid displays tiles correctly
- [ ] Skills modal opens with 60px top offset
- [ ] Modal shows bullets and examples

### API Integration
- [ ] `/api/chat/ask_grok` called when checkbox enabled
- [ ] Fallback to `/api/skills/ask` works
- [ ] `/api/ask` called when checkbox disabled
- [ ] Error messages are user-friendly

### Error Handling
- [ ] 401 error shows "LLM service not configured"
- [ ] 404 error shows "Session not found"
- [ ] 502/503 errors show "Service unavailable"
- [ ] Errors are localized (EN/RU)

## Rollback Procedure

If issues occur:

```powershell
# PowerShell
cd C:\PersonalProjects\ai-avatar
git log --oneline -10  # Find previous commit
git checkout <previous-commit-hash>
cd apps\miniapp-web
pnpm build
```

```bash
# Bash
cd /path/to/ai-avatar
git log --oneline -10  # Find previous commit
git checkout <previous-commit-hash>
cd apps/miniapp-web
pnpm build
```

## Troubleshooting

### Checkbox not appearing
- Check browser console for errors
- Verify `useSmartLLM` hook is imported
- Check localStorage is accessible

### LLM routing not working
- Verify API endpoints are accessible
- Check Network tab for request/response
- Verify `config.llmAvailable === true`

### State not persisting
- Check localStorage permissions
- Verify `SMART_LLM_ENABLED` key exists
- Check for storage quota issues

### Skills page still shows toggle
- Clear browser cache
- Verify `SkillsPage.tsx` changes are applied
- Check for build cache issues

## Environment Variables
No new environment variables required. Existing API configuration applies.

## Dependencies
No new dependencies added. Uses existing React hooks and API client.

## Notes
- localStorage key: `SMART_LLM_ENABLED`
- Default state: `false`
- State is global (shared across all chat instances)
- Checkbox disabled when `config.llmAvailable === false`

