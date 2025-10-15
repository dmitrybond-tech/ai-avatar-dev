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

The GitHub Actions workflow automatically:

1. **Build**: Builds Docker images for api, website, telegram
2. **Push**: Pushes images to GitHub Container Registry (GHCR)
3. **Deploy**: SSHs to VM and runs `docker compose pull && up -d`

**Triggered on:**
- Push to `main` branch
- Manual workflow dispatch

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

