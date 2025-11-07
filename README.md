# AI Avatar - Lightweight Chatbot Monorepo

A clean, production-ready monorepo for an AI Avatar chatbot with FastAPI backend, Astro frontend, and Telegram Web App integration.

## 🎯 Features

- **Backend API** (FastAPI): REST + WebSocket streaming, Telegram initData verification, TTS endpoint
- **Website** (Astro): Web chat UI with streaming, "Listen" button, talking head animation, Telegram Web App support
- **Telegram Bot**: Polling mode with Web App button
- **Infrastructure**: Docker Compose with Postgres + Redis
- **CI/CD**: GitHub Actions → GHCR → Ubuntu VM deployment

## 📋 Prerequisites

- **Windows 10/11** with PowerShell 7+
- **Docker Desktop** 4.x+ with Docker Compose v2
- **Node.js** 20 LTS
- **pnpm** 8.x+
- **Python** 3.12+ (for local development)
- **Git** 2.x+

## 🏗️ Architecture

```
ai-avatar/
├── apps/
│   ├── api/              # FastAPI backend
│   ├── website/          # Astro frontend (FSD)
│   └── telegram/         # Telegram bot worker
├── packages/
│   ├── shared/           # Shared TS types
│   └── clients/          # WS + REST clients
├── infra/
│   ├── compose/          # Docker Compose
│   └── scripts/          # Helper scripts
└── .github/workflows/    # CI/CD
```

## 🚀 Quick Start (Windows PowerShell)

### 1. Clone and Setup

```powershell
# Clone repository
cd C:\PersonalProjects
git clone https://github.com/your-username/ai-avatar.git
cd ai-avatar

# Install pnpm (if not already installed)
npm install -g pnpm@8.15.0

# Install Node dependencies
pnpm install
```

### 2. Configure Environment

```powershell
# Copy and edit environment file
cd infra\compose
Copy-Item env.example .env
notepad .env
```

**Required environment variables:**

```env
# Telegram Bot (get from @BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_USERNAME=your_bot_username
TG_WEBAPP_URL=https://your-domain.com/tg/miniapp

# JWT (generate a strong secret)
JWT_SECRET=your-strong-random-secret-here

# Public API URL (for production)
PUBLIC_API_BASE_URL=https://api.your-domain.com
```

### 3. Start Services

```powershell
# Using helper script
..\scripts\make.ps1 build
..\scripts\make.ps1 up

# Or directly with docker compose
docker compose up -d --build

# View logs
docker compose logs -f api
```

### 4. Verify Services

```powershell
# Check health
curl http://localhost:8080/healthz

# Open website
Start-Process "http://localhost:3000"
```

## 📦 Service Endpoints

| Service  | URL                          | Description           |
|----------|------------------------------|-----------------------|
| API      | http://localhost:8080        | REST + WebSocket API  |
| Website  | http://localhost:3000        | Web chat interface    |
| Telegram | -                            | Polling bot (no port) |
| Postgres | localhost:5432               | Database              |
| Redis    | localhost:6379               | Cache                 |

### API Routes

- `GET /healthz` - Health check
- `POST /chat` - Non-streaming chat
- `WS /chat/stream` - Streaming chat
- `POST /voice/tts` - Text-to-speech
- `POST /tg/verify` - Telegram initData verification

## 🤖 Telegram Bot Setup

### 1. Create Bot with BotFather

```
1. Open Telegram and search for @BotFather
2. Send /newbot
3. Follow prompts to name your bot
4. Copy the bot token
5. Send /setdomain and set your Web App URL
6. Send /mybots → Select bot → Menu Button → Set URL to your Web App
```

### 2. Configure Web App

```
1. Send /newapp to @BotFather
2. Select your bot
3. Provide:
   - App name: AI Avatar
   - Description: Your AI assistant
   - Photo: Upload a 640x360 image
   - Short name: aiavatar
   - Web App URL: https://your-domain.com/tg/miniapp
```

### 3. Update Environment

```powershell
# Edit .env with your bot token
cd infra\compose
notepad .env

# Update these values:
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_BOT_USERNAME=your_bot_username
TG_WEBAPP_URL=https://your-domain.com/tg/miniapp
```

### 4. Test Bot

```
1. Search for your bot in Telegram
2. Send /start
3. Send /app
4. Click "Open AI Avatar" button
5. Chat should open in Web App view
```

## 🔧 Development Commands

### PowerShell Commands

```powershell
# Start all services
.\infra\scripts\make.ps1 up

# Stop all services
.\infra\scripts\make.ps1 down

# View logs
.\infra\scripts\make.ps1 logs

# Rebuild images
.\infra\scripts\make.ps1 build

# Restart services
.\infra\scripts\make.ps1 restart

# Clean everything (removes volumes)
.\infra\scripts\make.ps1 clean
```

### Manual Docker Compose

```powershell
cd infra\compose

# Start
docker compose up -d

# Stop
docker compose down

# Rebuild specific service
docker compose build api
docker compose up -d api

# View logs for specific service
docker compose logs -f api

# Execute command in container
docker compose exec api python -c "print('Hello')"
```

### Local Development (without Docker)

**Backend:**

```powershell
cd apps\api

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run with PostgreSQL and Redis running
$env:POSTGRES_HOST="localhost"
$env:REDIS_URL="redis://localhost:6379/0"
python -m uvicorn app.main:app --reload --port 8080
```

**Website:**

```powershell
cd apps\website

# Install dependencies
pnpm install

# Run dev server
pnpm dev

# Build for production
pnpm build
pnpm preview
```

**Telegram Bot:**

```powershell
cd apps\telegram

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run bot
cd src
python bot.py
```

## 🚢 Production Deployment (Ubuntu VM)

### 1. Prepare Ubuntu VM

```bash
# SSH into your VM
ssh user@your-vm-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Create deployment directory
mkdir -p ~/ai-avatar-deploy
cd ~/ai-avatar-deploy
```

### 2. Setup Environment on VM

```bash
# Create .env file
nano .env

# Paste your production environment variables
# Update:
#   - TELEGRAM_BOT_TOKEN
#   - JWT_SECRET (generate new one for production)
#   - TG_WEBAPP_URL (your production domain)
#   - PUBLIC_API_BASE_URL (your production API URL)
#   - WEBSITE_ORIGIN (your production website URL)

# Download docker-compose.yml
curl -O https://raw.githubusercontent.com/your-username/ai-avatar/main/infra/compose/docker-compose.yml
```

### 3. Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

| Secret            | Description                      | Example                    |
|-------------------|----------------------------------|----------------------------|
| `SSH_HOST`        | VM IP address                    | `192.168.1.100`            |
| `SSH_USER`        | SSH username                     | `ubuntu`                   |
| `SSH_KEY`         | SSH private key (full content)   | `-----BEGIN RSA...`        |
| `SSH_PORT`        | SSH port (optional)              | `22`                       |
| `DEPLOY_PATH`     | Deployment directory on VM       | `/home/ubuntu/ai-avatar-deploy` |

**Generate SSH key (if needed):**

```powershell
# On Windows
ssh-keygen -t rsa -b 4096 -C "github-actions"
# Save to: C:\Users\YourName\.ssh\github_actions

# Copy public key to VM
Get-Content C:\Users\YourName\.ssh\github_actions.pub | ssh user@vm-ip "cat >> ~/.ssh/authorized_keys"

# Copy private key content to GitHub secret SSH_KEY
Get-Content C:\Users\YourName\.ssh\github_actions
```

### 4. Deploy

```powershell
# Push to main branch to trigger deployment
git add .
git commit -m "Initial deployment"
git push origin main

# Or manually trigger workflow
# Go to Actions → CI/CD Pipeline → Run workflow
```

### 5. Monitor Deployment

```bash
# SSH to VM and check logs
ssh user@your-vm-ip
cd ~/ai-avatar-deploy
docker compose logs -f
```

## 🎯 Telegram MiniApp Deployment

The MiniApp consists of three services: API, Bot, and Web. All components are deployed using pre-built images from GitHub Container Registry (GHCR) for production, with optional local builds for development.

### MiniApp Components

- **API** (`apps/miniapp-api`): FastAPI serving `/healthz`, `/rules`, handles Cal.com integration
- **Bot** (`apps/miniapp-bot`): Telegram bot using aiogram 3.7 with WebApp button support
- **Web** (`apps/miniapp-web`): Vite + React frontend served by Nginx

### Quick Start (Image-based Deployment)

1. **Setup Environment**

```bash
cd infra/compose
cp env.miniapp.example .env.miniapp
# Edit .env.miniapp and set TELEGRAM_TOKEN (required)
```

2. **Authenticate to GHCR**

```bash
# Login to GitHub Container Registry
docker login ghcr.io -u <your-github-username> -p <your-personal-access-token>

# Your PAT needs 'read:packages' permission
# Generate at: https://github.com/settings/tokens
```

3. **Pull and Start Services**

```bash
# Pull latest images and start all services
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml \
  --env-file infra/compose/.env.miniapp pull

docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml \
  --env-file infra/compose/.env.miniapp up -d
```

### MiniApp Helper Script

```bash
bash infra/compose/miniapp.sh config
bash infra/compose/miniapp.sh up api
bash infra/compose/miniapp.sh exec -T api env | egrep '^TELEGRAM_'
```

4. **Verify Services**

```bash
# Check API health
curl http://localhost:8081/healthz
# Expected: {"status":"ok"}

# Check rules endpoint
curl http://localhost:8081/rules?lang=ru
# Expected: JSON with labels and scenes

# Check bot logs
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml \
  --env-file infra/compose/.env.miniapp logs -f bot
# Expected: Bot shows "online" status, no errors about parse_mode; webhook is deleted on start (polling)

# Check web (if exposed)
curl http://localhost:5175
# Expected: HTML page (200 OK)
```

### Local Development (Build from Source)

For local development, you can build images from source:

```bash
# Use the build override file
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.build.yml \
  -f infra/compose/miniapp.runtime.yml --env-file infra/compose/.env.miniapp up -d --build
```

### Production Deployment (Ubuntu VM with Caddy)

On production, Caddy proxies `miniapp.dmitrybond.tech` to:
- API: `127.0.0.1:8081` (internal port)
- Web: `127.0.0.1:5175` (internal port)

**Deploy with Images:**

```bash
# Authenticate to GHCR
docker login ghcr.io -u <github-username> -p <PAT>

# Deploy using pre-built images
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml \
  --env-file infra/compose/.env.miniapp pull

docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml \
  --env-file infra/compose/.env.miniapp up -d
```

### Smoke Tests

```bash
# Test web app
curl -sI --http2 https://miniapp.dmitrybond.tech/miniapp/ | egrep -i '^(HTTP/|content-type|cache-control)'

# Test API health
curl -s --http2 https://miniapp.dmitrybond.tech/healthz && echo
# Expected: {"status":"ok"}

# Test API rules endpoint
curl -s --http2 'https://miniapp.dmitrybond.tech/rules?lang=ru' | head
# Expected: JSON with labels and scenes

# Check bot logs
docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml \
  --env-file infra/compose/.env.miniapp logs -n 120 bot
# Expected: Bot shows "online" status, no errors about parse_mode
```

### Common Issues

**Bot fails to start with `TypeError: parse_mode`**

- ✅ **Fixed**: Updated to aiogram 3.7 API using `DefaultBotProperties`
- ✅ **Verify**: Check `apps/miniapp-bot/main.py` imports `DefaultBotProperties` from `aiogram.client.default`
- ✅ **Verify**: Check `apps/miniapp-bot/requirements.txt` pins `aiogram==3.7.0`

**Bot crashes with "TELEGRAM_TOKEN is not set"**

- ✅ **Fixed**: Added early validation in `main.py`
- Check `.env.miniapp` file exists and contains `TELEGRAM_TOKEN=your_token_here`
- Ensure `.env.miniapp` is loaded: `docker compose -f infra/compose/miniapp.compose.yaml -f infra/compose/miniapp.runtime.yml --env-file infra/compose/.env.miniapp up -d`

**Runtime pip/npm installs in logs**

- ✅ **Fixed**: Removed runtime installs from `miniapp.compose.yaml`
- All dependencies are installed at Docker build-time via Dockerfiles
- Rebuild images: `docker compose -f infra/compose/miniapp.compose.yaml build --no-cache`

**Web app shows 404 or assets not loading**

- Verify Nginx is serving built files (check `apps/miniapp-web/Dockerfile` uses multi-stage build)
- Check Caddy configuration forwards to correct internal port (`127.0.0.1:5175`)
- Verify `VITE_API_BASE_URL` matches production domain

### Environment Variables

See `infra/compose/env.miniapp.example` for all required variables:

- **Required**: `TELEGRAM_TOKEN` (from @BotFather)
- **Required**: `TELEGRAM_BOT_NAME`
- **Required**: `WEBAPP_URL` (public URL for Telegram WebApp button)
- **Required**: `VITE_API_BASE_URL` (for frontend build)
- **Optional**: `CAL_USERNAME`, `CAL_EVENT_INTRO`, `CAL_HOST`, `DEFAULT_LANG`, `VITE_DEFAULT_LANG`

### Caddy Configuration Notes

Caddy proxies `miniapp.dmitrybond.tech` to internal Docker ports:
- API: `127.0.0.1:8081` (mapped from container port 8080)
- Web: `127.0.0.1:5175` (mapped from container port 80)

Ensure Caddy configuration includes reverse proxy rules for:
- `/healthz` → API
- `/rules` → API
- `/miniapp/` → Web app

See `infra/caddy/miniapp.caddy.inc` for example configuration.

## 🔐 Security Checklist

- [ ] Change `JWT_SECRET` to a strong random value
- [ ] Use environment-specific secrets (don't reuse dev secrets in prod)
- [ ] Enable HTTPS with valid SSL certificates (use Let's Encrypt)
- [ ] Configure firewall rules (allow only necessary ports)
- [ ] Set strong PostgreSQL password
- [ ] Regularly update Docker images
- [ ] Review CORS settings in production
- [ ] Enable GitHub branch protection rules
- [ ] Use GitHub secrets for sensitive data
- [ ] Backup database regularly

## 📊 Database Management

### Backup

```powershell
# Backup PostgreSQL
docker compose exec -T db pg_dump -U avatar avatar > backup.sql

# With timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
docker compose exec -T db pg_dump -U avatar avatar > "backup_$timestamp.sql"
```

### Restore

```powershell
# Restore from backup
Get-Content backup.sql | docker compose exec -T db psql -U avatar avatar
```

### Access Database

```powershell
# PostgreSQL CLI
docker compose exec db psql -U avatar avatar

# Redis CLI
docker compose exec redis redis-cli
```

## 🧪 Testing

### API Health Check

```powershell
# Test health endpoint
Invoke-RestMethod http://localhost:8080/healthz

# Test chat endpoint
$body = @{
    message = "Hello!"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:8080/chat -Body $body -ContentType "application/json"
```

### WebSocket Test

```javascript
// In browser console on http://localhost:3000
const ws = new WebSocket('ws://localhost:8080/chat/stream');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.onopen = () => ws.send(JSON.stringify({ type: 'user_message', text: 'Hello!' }));
```

## 🐛 Troubleshooting

### Services Won't Start

```powershell
# Check Docker daemon
docker info

# Check container logs
docker compose logs

# Check specific service
docker compose logs api

# Restart Docker Desktop
# Right-click Docker Desktop icon → Restart
```

### Database Connection Issues

```powershell
# Check if DB is running
docker compose ps db

# Check DB logs
docker compose logs db

# Test connection
docker compose exec db psql -U avatar -d avatar -c "SELECT 1"
```

### Port Already in Use

```powershell
# Find process using port 8080
netstat -ano | findstr :8080

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or change port in .env
# API_PORT=8081
```

### Build Failures

```powershell
# Clear Docker build cache
docker builder prune -a

# Rebuild without cache
docker compose build --no-cache

# Check disk space
docker system df
docker system prune -a
```

### Telegram Bot Not Responding

1. Check bot token is correct
2. Verify bot is running: `docker compose logs telegram`
3. Test with /start command
4. Check WebApp URL is accessible publicly
5. Verify initData verification in API logs

## 📝 Project Structure Details

### Backend (FastAPI)

- **`core/`**: Settings, logging, security, middleware
- **`schemas/`**: Pydantic models for request/response
- **`services/`**: Business logic (chat, TTS, sessions)
- **`adapters/web/`**: HTTP and WebSocket routers
- **`repos/`**: Database access layer
- **`db/`**: SQL migrations and init scripts

### Frontend (Astro + FSD)

- **`pages/`**: Routes (`/`, `/tg/miniapp`)
- **`features/`**: Feature modules (avatar-chat, talking-head)
- **`entities/`**: Business entities (message, session)
- **`shared/`**: Shared UI components, API clients, utilities

### Shared Packages

- **`@ai-avatar/shared`**: TypeScript types and constants
- **`@ai-avatar/clients`**: REST and WebSocket client SDKs

## 🔄 CI/CD Pipeline

The `CI — Main Images` workflow builds and pushes container images for the miniapp frontend and API whenever we update the default branches.

- **Automatic trigger**: Every push to `main` or `master` runs the workflow and publishes images tagged `:main` and `:${SHA}` to GHCR.
- **Manual trigger**: Go to **Actions → CI — Main Images → Run workflow**, pick the branch (default is the currently selected branch), and press **Run workflow** to queue a manual build.

If a service Dockerfile is missing (for example when a component is not part of the repo), the job skips that image without failing the run.

## 🎨 Customization

### Change LLM Provider

Edit `apps/api/src/app/services/chat.py`:

```python
# Replace StubLLMProvider with your provider
# Example: OpenAI, Anthropic, etc.
class OpenAIProvider(LLMProvider):
    async def stream_chat(self, messages, **kwargs):
        # Your implementation
        pass
```

### Change TTS Provider

Edit `apps/api/src/app/services/tts.py`:

```python
# Replace StubTTSProvider with your provider
# Example: ElevenLabs, Google TTS, etc.
class ElevenLabsProvider(TTSProvider):
    async def synthesize(self, text, voice):
        # Your implementation
        pass
```

### Customize Talking Head

Edit `apps/website/src/features/talking-head/TalkingHead.astro` to change appearance and animations.

## 📚 Tech Stack Versions

| Technology         | Version  |
|--------------------|----------|
| Python             | 3.12     |
| FastAPI            | 0.115.x  |
| Uvicorn            | 0.30.x   |
| python-telegram-bot| 21.x     |
| asyncpg            | 0.29.x   |
| redis              | 5.x      |
| pyjwt              | 2.9.x    |
| Node.js            | 20 LTS   |
| pnpm               | 8.15.0   |
| Astro              | 5.x      |
| TypeScript         | 5.6.x    |
| Postgres           | 16       |
| Redis              | 7-alpine |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

- **Issues**: https://github.com/your-username/ai-avatar/issues
- **Discussions**: https://github.com/your-username/ai-avatar/discussions

## 🎯 Roadmap

Future enhancements (not in MVP):

- [ ] Connect real LLM provider (OpenAI, Anthropic)
- [ ] Connect real TTS provider (ElevenLabs, Google TTS)
- [ ] Add RAG with vector database
- [ ] Implement rate limiting with Redis
- [ ] Add user authentication
- [ ] Support multiple personas
- [ ] Add voice input (STT)
- [ ] Implement conversation history UI
- [ ] Add admin dashboard
- [ ] Kubernetes deployment option

---

**Built with ❤️ using Feature-Sliced Design**

