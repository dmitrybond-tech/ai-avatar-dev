# Rasa Bot - Quick Start Guide

## 🚀 Setup in 5 Minutes

### Step 1: Create Notion Database

1. Go to https://www.notion.so/my-integrations
2. Click **"+ New integration"**
3. Name it (e.g., "Rasa Skills Bot")
4. Copy the **Internal Integration Secret** → This is your `NOTION_SECRET`

5. Create a new database in Notion with these columns:

| Column Name | Type | Required |
|------------|------|----------|
| Name | Title | ✅ |
| Level | Select | ✅ |
| Years | Number | ✅ |
| Keywords | Rich Text | ✅ |
| Tags | Multi-select | Optional |
| Examples | Rich Text | Optional |

6. Share the database with your integration (click "..." → "Add connections")
7. Copy the database ID from URL: `https://notion.so/workspace/{DATABASE_ID}?v=...`

### Step 2: Create Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Choose a name and username
4. Copy the **token** → This is your `TELEGRAM_TOKEN`
5. Note the **username** (without @) → This is your `TELEGRAM_BOT_NAME`

### Step 3: Configure Environment

```powershell
# Copy example to root directory
Copy-Item apps\rasa-bot\env.rasa-bot.example .env.rasa-bot

# Edit .env.rasa-bot and fill in:
# - TELEGRAM_TOKEN=your_token_here
# - TELEGRAM_BOT_NAME=your_bot_username
# - NOTION_SECRET=your_notion_secret
# - NOTION_DB=your_database_id
```

### Step 4: Train Model

```powershell
.\scripts\rasa-bot-train.ps1
```

Wait 2-5 minutes for training to complete.

### Step 5: Start Services

```powershell
.\scripts\rasa-bot-dev.ps1
```

### Step 6: Enable Telegram

```powershell
docker exec -it rasa-bot rasa run --connector telegram --port 5005
```

Keep this terminal open.

### Step 7: Test!

Open Telegram and message your bot:

```
You: привет
Bot: Привет! Я бот-помощник. Спроси меня о навыках и опыте...

You: умеешь ли ты kubernetes?
Bot: ✅ Да, есть опыт с Kubernetes
     Уровень: Advanced
     Опыт: 3 года
```

## 🛠️ Useful Commands

```powershell
# Stop services
.\scripts\rasa-bot-down.ps1

# View logs
docker compose -f infra\compose\rasa-bot.compose.yaml logs -f

# Retrain after changes
.\scripts\rasa-bot-train.ps1

# Refresh Notion cache (in Telegram)
/refresh
```

## 📝 Example Notion Database Entry

**Name:** Kubernetes  
**Level:** Advanced  
**Years:** 3  
**Keywords:** k8s, kubernetes, кубернетес, кубер  
**Tags:** DevOps, Cloud  
**Examples:** Deployed multi-region production clusters with 200+ microservices on AWS EKS. Implemented GitOps with ArgoCD and FluxCD.

## 🐛 Troubleshooting

**Problem:** Bot doesn't respond  
**Solution:** Make sure Telegram polling is running (Step 6)

**Problem:** "No trained model found"  
**Solution:** Run `.\scripts\rasa-bot-train.ps1`

**Problem:** "Failed to fetch from Notion"  
**Solution:** Check NOTION_SECRET and NOTION_DB in .env.rasa-bot

**Problem:** Bot says "Не нашёл информацию"  
**Solution:** Add more keywords to your Notion entries

## 📚 Full Documentation

See [README.md](./README.md) for comprehensive documentation.

