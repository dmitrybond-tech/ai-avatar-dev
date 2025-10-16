# Telegram Mini App - Quick Start Guide

Fast-track setup guide for the new Telegram Mini App integration.

## 🚀 Quick Setup (5 minutes)

### 1. Create Telegram Bot
```
1. Open Telegram and message @BotFather
2. Send: /newbot
3. Choose a name and username
4. Copy the token provided
```

### 2. Create Notion Integration
```
1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name it (e.g., "AI Avatar Skills")
4. Copy the Internal Integration Token
5. Create a database with these properties:
   - name (Title)
   - level (Select)
   - years (Number)
   - tags (Multi-select)
   - keywords (Rich text)
   - examples (Rich text)
6. Share your database with the integration
7. Copy the database ID from URL
```

### 3. Configure Environment
```powershell
# Copy template
cp env.miniapp.example infra/compose/.env.miniapp

# Edit configuration
notepad infra/compose/.env.miniapp
```

**Required values:**
```env
TELEGRAM_TOKEN=your_token_from_botfather
NOTION_DB=your_notion_database_id
NOTION_SECRET=your_notion_integration_secret
WEBAPP_URL=http://localhost:5173/miniapp/
CAL_LINK=https://cal.com/youraccount
```

### 4. Start Services
```powershell
# Start backend services (gateway + bot)
.\scripts\miniapp-up.ps1

# In another terminal, start frontend
cd apps\website
pnpm dev
```

### 5. Test in Telegram
```
1. Open Telegram and find your bot
2. Send: /start
3. Tap "🤖 Open Assistant" button
4. Ask a question (e.g., "Python")
```

---

## 📁 What Was Added

### New Directories
```
apps/miniapp-gateway/     - FastAPI service
apps/miniapp-bot/         - Telegram bot
apps/miniapp-frontend/    - Documentation
apps/website/src/pages/miniapp/  - Frontend page
```

### New Files
```
env.miniapp.example                  - Environment template
apps/miniapp-gateway/main.py         - Gateway API
apps/miniapp-gateway/requirements.txt
apps/miniapp-gateway/Dockerfile
apps/miniapp-gateway/README.md
apps/miniapp-bot/bot.py              - Bot logic
apps/miniapp-bot/requirements.txt
apps/miniapp-bot/Dockerfile
apps/miniapp-bot/README.md
apps/website/src/pages/miniapp/index.astro  - Chat UI
apps/website/env.example
apps/miniapp-frontend/README.md
infra/compose/miniapp.compose.yaml   - Docker orchestration
scripts/miniapp-up.ps1               - Start script
scripts/miniapp-down.ps1             - Stop script
```

---

## 🔧 Common Commands

### Start/Stop Services
```powershell
# Start everything
.\scripts\miniapp-up.ps1

# Stop services
.\scripts\miniapp-down.ps1

# View logs
docker compose -f infra/compose/miniapp.compose.yaml logs -f

# Restart a service
docker restart miniapp-gateway
docker restart miniapp-bot
```

### Frontend Development
```powershell
cd apps/website

# Install dependencies (first time)
pnpm install

# Start dev server
pnpm dev

# Build for production
pnpm build
```

### Testing Endpoints
```powershell
# Health check
curl http://localhost:8080/healthz

# Test query
curl -X POST http://localhost:8080/reply `
  -H "Content-Type: application/json" `
  -d '{"text":"Python"}'

# Refresh cache
curl -X POST http://localhost:8080/refresh
```

---

## 🐛 Troubleshooting

### Gateway won't start
```powershell
# Check logs
docker logs miniapp-gateway

# Common issues:
# - Missing NOTION_SECRET or NOTION_DB in .env.miniapp
# - Invalid Notion credentials
# - Port 8080 already in use
```

### Bot not responding
```powershell
# Check logs
docker logs miniapp-bot

# Common issues:
# - Invalid TELEGRAM_TOKEN
# - Gateway not healthy (bot depends on it)
# - Another bot instance already polling
```

### Frontend can't connect
```powershell
# Check environment
cat apps/website/.env

# Should have:
# PUBLIC_GATEWAY_URL=http://localhost:8080

# Test gateway directly
curl http://localhost:8080/healthz
```

### WebApp button doesn't work
```
Common issues:
- WEBAPP_URL must be publicly accessible
- For local testing, use ngrok: ngrok http 5173
- Production requires HTTPS
- URL must include protocol (http:// or https://)
```

---

## 📊 Architecture

```
┌──────────────┐
│ Telegram Bot │  ← Long polling, sends WebApp button
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Mini App UI  │  ← Astro page at /miniapp/
│ (Frontend)   │  ← Sends POST /reply
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Gateway    │  ← FastAPI service
│   (API)      │  ← Fuzzy matching with rapidfuzz
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Notion DB   │  ← Source of truth for skills
└──────────────┘
```

---

## 📖 Documentation

- **`MINIAPP_CHANGES.md`** - Complete change log with detailed documentation
- **`MINIAPP_FILES_SUMMARY.md`** - File-by-file breakdown and statistics
- **`apps/miniapp-gateway/README.md`** - API documentation
- **`apps/miniapp-bot/README.md`** - Bot setup and usage
- **`apps/miniapp-frontend/README.md`** - Frontend integration guide

---

## ✅ Verification Checklist

After setup, verify:
- [ ] `.\scripts\miniapp-up.ps1` starts without errors
- [ ] `curl http://localhost:8080/healthz` returns `{"ok":true}`
- [ ] `docker ps` shows `miniapp-gateway` and `miniapp-bot` running
- [ ] Telegram bot responds to `/start` with WebApp button
- [ ] Frontend accessible at `http://localhost:5173/miniapp/`
- [ ] Sending message in Mini App returns response
- [ ] Notion data appears in responses

---

## 🎯 Next Steps

### For Local Development
1. ✅ Complete quick setup above
2. Add skills to your Notion database
3. Test queries in the Mini App
4. Customize styling in `apps/website/src/pages/miniapp/index.astro`

### For Production Deployment
1. Deploy frontend to hosting service (Vercel, Netlify, etc.)
2. Deploy gateway to server (Docker on Ubuntu VM)
3. Update `WEBAPP_URL` to production URL (HTTPS)
4. Configure reverse proxy for gateway (nginx/caddy)
5. Consider switching bot to webhooks for better scalability
6. Set up monitoring and logging

### For Rasa Migration (Future)
1. Keep this Mini App working as-is
2. Replace gateway with Rasa proxy
3. Update `PUBLIC_GATEWAY_URL` in frontend
4. No changes needed to bot or UI

---

## 💡 Tips

**Notion Database:**
- Add keywords and tags for better fuzzy matching
- Use consistent naming conventions
- Test queries match expected skills

**Bot Configuration:**
- Use a descriptive bot name and username
- Set bot description via BotFather: `/setdescription`
- Set bot about text: `/setabouttext`
- Add profile picture: `/setuserpic`

**Development Workflow:**
1. Edit code
2. Rebuild: `.\scripts\miniapp-down.ps1` then `.\scripts\miniapp-up.ps1`
3. Test in Mini App
4. Check logs if issues

**Windows-Specific:**
- PowerShell scripts are already configured
- No WSL required
- Docker Desktop must be running
- Use PowerShell (not CMD) to run scripts

---

## 🎉 Success Indicators

You've successfully set up the Mini App when:
1. ✅ Gateway health check passes
2. ✅ Bot sends WebApp button
3. ✅ Mini App opens in Telegram
4. ✅ Queries return Notion data
5. ✅ Booking link works

---

## 📞 Getting Help

1. Check service logs: `docker logs miniapp-gateway` or `docker logs miniapp-bot`
2. Review detailed docs in `MINIAPP_CHANGES.md`
3. Check individual service READMEs
4. Verify environment configuration in `.env.miniapp`

---

**Ready to start?** Run: `.\scripts\miniapp-up.ps1` 🚀

