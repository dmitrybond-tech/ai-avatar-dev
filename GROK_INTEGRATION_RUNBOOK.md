# Grok LLM Integration Runbook

## Quick Start

### 1. Environment Setup

Add to `.env.miniapp` (do not commit secrets):

```bash
# xAI / Grok
XAI_API_KEY=__SET_ME_IN_PROD__
LLM_PROVIDER=grok
GROK_MODEL=grok-4
GROK_BASE_URL=https://api.x.ai
GROK_MAX_TOKENS=512
GROK_TEMPERATURE=0.3
```

### 2. Deploy

```bash
cd infra/compose

# Rebuild API service
docker compose --env-file .env.miniapp \
  -f miniapp.compose.yaml \
  -f miniapp.runtime.yml \
  -f miniapp.stack.yml \
  -f miniapp.llm.override.yml \
  build api

# Restart services
docker compose --env-file .env.miniapp \
  -f miniapp.compose.yaml \
  -f miniapp.runtime.yml \
  -f miniapp.stack.yml \
  -f miniapp.llm.override.yml \
  up -d api bot
```

### 3. Verify

```bash
# Health check
curl -i https://miniapp.dmitrybond.tech/api/healthz

# Skills list
curl -s https://miniapp.dmitrybond.tech/api/skills?lang=ru | jq '.[0]'

# Ask endpoint
curl -s -X POST https://miniapp.dmitrybond.tech/api/skills/ask \
  -H "Content-Type: application/json" \
  -d '{"q":"Можешь ли ты автоматизировать ETL на Python?","lang":"ru"}' | jq .
```

## Telegram Bot Usage

1. **Enable Smart LLM:**
   - Send `/smart on` command, OR
   - Tap inline button "Smart LLM reply: OFF" to toggle ON

2. **Ask Questions:**
   - With Smart LLM enabled, send any text message
   - Bot will call Grok API and reply with skills-grounded answer

3. **Disable Smart LLM:**
   - Send `/smart off` command, OR
   - Tap inline button "Smart LLM reply: ON" to toggle OFF

## Troubleshooting

### API Returns 401
- Check `XAI_API_KEY` is set in `.env.miniapp`
- Verify compose override is loaded

### API Returns 502
- Check Grok API is accessible
- Verify `GROK_MODEL` is valid (e.g., `grok-4`)
- Check API logs for detailed error

### API Returns 503
- Verify `SKILLS_CSV_PATH` points to valid CSV file
- Check CSV file exists and is readable
- If `SKILLS_SOURCE=csv`, file must exist

### Bot Not Responding
- Check `API_BASE_URL` env var (default: `http://api:8000`)
- Verify bot can reach API service
- Check bot logs for connection errors

### CSV Not Loading
- Verify CSV file encoding (UTF-8 or UTF-8 with BOM)
- Check CSV headers match expected format
- Review API logs for CSV parsing errors

## API Endpoints

### POST /api/skills/ask

**Request:**
```json
{
  "q": "Can you automate ETL in Python?",
  "lang": "en",
  "selected": ["python", "etl"]
}
```

**Response:**
```json
{
  "answer": "Yes, Dima can automate ETL processes...",
  "used_skills": ["python", "etl", "automation"],
  "model": "grok-4",
  "tokens_estimate": 150
}
```

## Files Changed

1. `apps/miniapp-api/requirements.txt` - Dependencies
2. `infra/compose/miniapp.llm.override.yml` - Compose override
3. `apps/miniapp-api/app/services/skills_loader.py` - CSV loader
4. `apps/miniapp-api/app/services/llm_grok.py` - Grok client
5. `apps/miniapp-api/routers/skills.py` - Ask endpoint
6. `apps/miniapp-bot/main.py` - Bot toggle

## Notes

- Toggle state is in-memory (process-lifetime), resets on bot restart
- CSV loader caches based on file mtime
- Grok timeout: 30 seconds
- No secrets logged or committed

