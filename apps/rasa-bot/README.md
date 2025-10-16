# Rasa OSS Assistant

Minimal Rasa OSS bot for Telegram with Notion-based skills lookup. This bot is **isolated** from the existing AI Avatar services and does not modify any existing routes or apps.

## Features

- ✅ Telegram long polling (no webhooks required)
- ✅ Notion database integration for skills/experience
- ✅ Fuzzy matching with RapidFuzz
- ✅ 10-minute in-memory cache
- ✅ Russian language support
- ✅ Deterministic Docker builds with pinned versions

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│  Telegram   │─────▶│ Rasa Core    │─────▶│ Action Server   │
│   Polling   │      │  (3.6.20)    │      │   (SDK 3.6.2)   │
└─────────────┘      └──────────────┘      └─────────────────┘
                            │                        │
                            │                        ▼
                            │                ┌─────────────────┐
                            │                │  Notion API     │
                            │                │  (Skills DB)    │
                            │                └─────────────────┘
                            ▼
                     ┌──────────────┐
                     │   NLU Model  │
                     │ DIET+Rules   │
                     └──────────────┘
```

## Prerequisites

- Docker and Docker Compose
- PowerShell 7+ (for Windows development)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Notion Integration and Database

## Quick Start

### 1. Set up Notion Database

Create a Notion database with the following properties:

| Property Name | Type | Description | Example |
|--------------|------|-------------|---------|
| **Name** (or **Название**) | Title | Skill/technology name | "Kubernetes" |
| **Level** (or **Уровень**) | Select or Rich Text | Proficiency level | "Advanced" |
| **Years** (or **Лет**) | Number | Years of experience | 3 |
| **Tags** (or **Теги**) | Multi-select | Categories | "DevOps", "Cloud" |
| **Keywords** (or **Ключевые слова**) | Rich Text or Multi-select | Search keywords (comma-separated if Rich Text) | "k8s, kubernetes, кубер" |
| **Examples** (or **Примеры**) | Rich Text | Project examples | "Deployed multi-region..." |

**Notion Setup:**
1. Create a new integration at https://www.notion.so/my-integrations
2. Copy the **Internal Integration Secret** (this is `NOTION_SECRET`)
3. Share your database with the integration
4. Get the database ID from the URL: `https://notion.so/workspace/{DATABASE_ID}?v=...`

### 2. Create Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the **bot token** (this is `TELEGRAM_TOKEN`)
4. Note the **bot username** without @ (this is `TELEGRAM_BOT_NAME`)

### 3. Train the Model

```powershell
.\scripts\rasa-bot-train.ps1
```

This will:
- Validate the Rasa folder structure
- Pull the `rasa/rasa:3.6.20` image if needed
- Train the model with DIET (25 epochs) + Rules
- Save model to `apps/rasa-bot/rasa/models/`

**Expected output:**
```
✓ Training completed successfully!
Model saved to: apps\rasa-bot\rasa\models
```

### 4. Start the Bot

```powershell
.\scripts\rasa-bot-dev.ps1
```

First run will:
- Prompt for environment variables (TELEGRAM_TOKEN, NOTION_SECRET, etc.)
- Create `.env.rasa-bot` from `.env.rasa-bot.example`
- Start Rasa and Action Server containers

**Services will be available at:**
- Rasa API: http://localhost:5005
- Action Server: http://localhost:5055

### 5. Enable Telegram Polling

After services start, run:

```powershell
docker exec -it rasa-bot rasa run --connector telegram --port 5005
```

This starts the Telegram polling connector. Keep this terminal open.

**Note:** For background polling, modify the `rasa-bot.compose.yaml` command to include `--connector telegram`.

### 6. Test the Bot

Open Telegram and message your bot:

```
User: привет
Bot:  Привет! Я бот-помощник. Спроси меня о навыках и опыте...

User: умеешь ли ты kubernetes?
Bot:  ✅ Да, есть опыт с Kubernetes
      Уровень: Advanced
      Опыт: 3 года
      Область: DevOps, Cloud
      
      Примеры:
      Deployed multi-region clusters...
```

## Commands

### PowerShell Scripts

| Script | Description |
|--------|-------------|
| `.\scripts\rasa-bot-train.ps1` | Train the Rasa model |
| `.\scripts\rasa-bot-dev.ps1` | Start services (Rasa + Actions) |
| `.\scripts\rasa-bot-down.ps1` | Stop services |

### Docker Commands

```powershell
# View logs
docker compose -f infra/compose/rasa-bot.compose.yaml logs -f

# Shell access to Rasa container
docker exec -it rasa-bot bash

# Shell access to Actions container
docker exec -it rasa-actions bash

# Restart services
docker compose -f infra/compose/rasa-bot.compose.yaml restart

# Check status
docker compose -f infra/compose/rasa-bot.compose.yaml ps
```

### Bot Commands

Send these to your bot in Telegram:

| Command | Description |
|---------|-------------|
| `привет` | Greet the bot |
| `умеешь ли ты <skill>?` | Ask about a specific skill |
| `/refresh` | Force reload Notion cache |
| `пока` | Say goodbye |

## Configuration

### Environment Variables

All configuration is in `.env.rasa-bot`:

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_TOKEN` | Yes | Bot token from @BotFather |
| `TELEGRAM_BOT_NAME` | Yes | Bot username without @ |
| `NOTION_SECRET` | Yes | Notion integration secret |
| `NOTION_DB` | Yes | Notion database ID |
| `CAL_LINK` | No | Calendar/meeting link (appended to responses) |
| `RASA_LOG_LEVEL` | No | Logging level (default: INFO) |

### Cache Configuration

The action server caches Notion data in memory:
- **TTL:** 10 minutes
- **Refresh:** Automatic on expiry or manual via `/refresh` command

To change TTL, edit `CACHE_TTL_SECONDS` in `apps/rasa-bot/actions/actions.py`.

### NLU Configuration

Training parameters in `apps/rasa-bot/rasa/config.yml`:

```yaml
DIETClassifier:
  epochs: 25  # Balanced for cheap/fast training
  
TEDPolicy:
  epochs: 25  # Keep in sync with DIET
```

## Project Structure

```
apps/rasa-bot/
├── rasa/                    # Rasa core configuration
│   ├── config.yml           # Pipeline and policy config
│   ├── domain.yml           # Intents, responses, actions
│   ├── credentials.yml      # Telegram connector config
│   ├── endpoints.yml        # Action server endpoint
│   ├── data/
│   │   ├── nlu.yml         # Training examples (RU)
│   │   └── rules.yml       # Conversation rules
│   └── models/             # Trained models (auto-generated)
├── actions/                 # Custom action server
│   ├── requirements.txt    # Python dependencies
│   └── actions.py          # Notion integration + fuzzy match
└── README.md               # This file

infra/compose/
└── rasa-bot.compose.yaml   # Docker Compose config (isolated)

scripts/
├── rasa-bot-train.ps1      # Train model (PowerShell)
├── rasa-bot-dev.ps1        # Start services (PowerShell)
└── rasa-bot-down.ps1       # Stop services (PowerShell)

.env.rasa-bot.example        # Environment variables template
.env.rasa-bot                # Your local config (git-ignored)
```

## Troubleshooting

### Issue: "No trained model found"

**Solution:** Run training first:
```powershell
.\scripts\rasa-bot-train.ps1
```

### Issue: "Failed to fetch from Notion"

**Check:**
1. `NOTION_SECRET` and `NOTION_DB` are set correctly in `.env.rasa-bot`
2. Notion database is shared with your integration
3. Database properties match expected schema (see Quick Start §1)

**Debug:**
```powershell
# Check action server logs
docker logs rasa-actions -f
```

### Issue: Bot doesn't respond on Telegram

**Check:**
1. Telegram polling is running:
   ```powershell
   docker exec -it rasa-bot rasa run --connector telegram --port 5005
   ```
2. `TELEGRAM_TOKEN` and `TELEGRAM_BOT_NAME` are correct
3. Bot is started (talk to @BotFather, use `/mybots` -> your bot -> ensure it's not stopped)

### Issue: "No good match found"

The fuzzy match threshold is 60%. To improve matching:

1. Add more **keywords** in Notion (especially Russian variants)
2. Add more **NLU examples** in `apps/rasa-bot/rasa/data/nlu.yml`
3. Retrain the model: `.\scripts\rasa-bot-train.ps1`

### Issue: Docker volume mount issues on Windows

**Solution:** Ensure Docker Desktop has access to your drive:
- Docker Desktop → Settings → Resources → File Sharing
- Add `C:\PersonalProjects`

## Development

### Adding New Intents

1. Add intent to `apps/rasa-bot/rasa/domain.yml`
2. Add examples to `apps/rasa-bot/rasa/data/nlu.yml`
3. Add rule or story to `apps/rasa-bot/rasa/data/rules.yml`
4. Retrain: `.\scripts\rasa-bot-train.ps1`

### Adding New Actions

1. Implement action class in `apps/rasa-bot/actions/actions.py`
2. Register action in `apps/rasa-bot/rasa/domain.yml` under `actions:`
3. Restart services: `.\scripts\rasa-bot-down.ps1` then `.\scripts\rasa-bot-dev.ps1`

### Updating Dependencies

**Constraints:** Versions are pinned for determinism. To update:

1. Edit `apps/rasa-bot/actions/requirements.txt`
2. Rebuild action server:
   ```powershell
   docker compose -f infra/compose/rasa-bot.compose.yaml up -d --build actions
   ```

**Pinned versions:**
- Rasa: 3.6.20
- Rasa SDK: 3.6.2
- RapidFuzz: 3.9.6
- Requests: 2.32.3

## Production Deployment

For production on Ubuntu VM:

1. Copy repository to VM
2. Copy `.env.rasa-bot` with production values
3. Train model (on VM or locally, then copy to VM):
   ```bash
   docker run --rm -v $(pwd)/apps/rasa-bot/rasa:/app rasa/rasa:3.6.20 train
   ```
4. Start services:
   ```bash
   docker compose -f infra/compose/rasa-bot.compose.yaml up -d
   ```
5. Enable Telegram polling in background:
   ```bash
   docker exec -d rasa-bot rasa run --connector telegram --port 5005
   ```

**Alternative:** Modify `rasa-bot.compose.yaml` to include `--connector telegram` in the command for automatic polling on startup.

### Monitoring

```bash
# Check service health
docker compose -f infra/compose/rasa-bot.compose.yaml ps

# View logs
docker compose -f infra/compose/rasa-bot.compose.yaml logs -f

# Check Notion cache
docker exec rasa-actions cat /app/actions/actions.py | grep CACHE_TTL_SECONDS
```

## Isolation Notes

This bot is **completely isolated** from existing AI Avatar services:

- ✅ No changes to `apps/api`, `apps/telegram`, `apps/website`
- ✅ No changes to existing Docker Compose files
- ✅ No changes to CI/CD configuration
- ✅ Separate network (`rasa-network`)
- ✅ Separate ports (5005, 5055)
- ✅ Separate environment file (`.env.rasa-bot`)

You can safely remove the bot by deleting:
- `apps/rasa-bot/`
- `infra/compose/rasa-bot.compose.yaml`
- `scripts/rasa-bot-*.ps1`
- `.env.rasa-bot`

## License

Same as parent AI Avatar project.

## Support

For issues specific to this bot integration, check:
- Rasa docs: https://rasa.com/docs/rasa/
- Notion API: https://developers.notion.com/
- Telegram Bot API: https://core.telegram.org/bots/api

