# Change Log

## v0.1.0 - Initial Scaffold (2025-10-15)

### 1. Root Configuration
- Created monorepo structure with pnpm workspaces
- Added `.gitignore` with Python, Node, Docker exclusions
- Added `.editorconfig` for consistent code style
- Created root `package.json` with workspace configuration
- Added `pnpm-workspace.yaml` for monorepo setup

### 2. Shared Packages (`packages/`)

#### `packages/shared`
- TypeScript types for chat messages, personas, WebSocket envelopes
- HTTP request/response types (ChatRequest, ChatResponse, TTSRequest, TTSResponse)
- Telegram verification types
- Default persona presets
- Shared constants (API routes, session expiry, rate limits)

#### `packages/clients`
- `RestClient`: HTTP client for chat, TTS, Telegram verification, health checks
- `WsClient`: WebSocket client with auto-reconnect, exponential backoff, event listeners
- Full TypeScript type safety with shared types

### 3. Backend API (`apps/api`)

#### Core Infrastructure
- `core/settings.py`: Pydantic settings with environment variable support
- `core/logging.py`: Structured logging configuration
- `core/security.py`: Telegram initData HMAC verification, JWT token generation/verification
- `requirements.txt`: Pinned versions (FastAPI 0.115.5, asyncpg 0.29.0, etc.)

#### Database Layer
- `db/init.sql`: PostgreSQL schema (sessions, messages tables with indexes)
- `db/connection.py`: AsyncPG connection pool with automatic initialization
- `repos/sessions.py`: Session CRUD operations
- `repos/messages.py`: Message storage and retrieval (last N messages)

#### Services
- `services/chat.py`: Chat orchestration with streaming support
  - `LLMProvider` interface for pluggable LLM backends
  - `StubLLMProvider` for MVP (word-by-word streaming echo)
  - Message history management (last 5 messages)
- `services/tts.py`: Text-to-speech service
  - `TTSProvider` interface
  - `StubTTSProvider` generates valid WAV files (440Hz beep)
  - File storage under `/data/tts/`

#### HTTP & WebSocket Adapters
- `adapters/web/health.py`: Health check endpoint
- `adapters/web/chat.py`: REST chat endpoint
- `adapters/web/chat_ws.py`: WebSocket streaming chat with token auth
- `adapters/web/voice.py`: TTS endpoint
- `adapters/web/telegram.py`: Telegram initData verification and session creation

#### Application Entry
- `main.py`: FastAPI app with CORS, static file serving, router registration, lifespan management
- Dockerfile: Python 3.12-slim with optimized layer caching

### 4. Frontend Website (`apps/website`)

#### Configuration
- `package.json`: Astro 5.0.5, TypeScript 5.6.3
- `astro.config.mjs`: Static output, Vite aliases
- `tsconfig.json`: Strict mode, workspace path mappings

#### Shared Layer (FSD)
- `shared/ui/Button.astro`: Reusable button component with variants
- `shared/lib/config.ts`: Client-side API configuration

#### Entities Layer (FSD)
- `entities/message/Message.astro`: Message display component (user/assistant)

#### Features Layer (FSD)
- `features/avatar-chat/AvatarChat.astro`:
  - WebSocket-based streaming chat UI
  - Message history display
  - Typing indicator
  - Send button with Enter key support
  - Listen button for TTS playback
  - Audio event dispatching for talking head
- `features/talking-head/TalkingHead.astro`:
  - Animated avatar head with gradient face
  - Mouth animation synchronized with audio playback
  - CSS animations with `requestAnimationFrame`

#### Pages (Routes)
- `pages/index.astro`: Main web chat page (/)
- `pages/tg/miniapp.astro`: Telegram Web App page (/tg/miniapp)
  - Telegram WebApp SDK integration
  - Theme synchronization (light/dark)
  - initData verification flow
  - Token-based WebSocket connection

#### Layouts
- `layouts/Layout.astro`: Base HTML layout with global styles
- Dockerfile: Multi-stage build with Node 20-alpine, static file serving with `serve`

### 5. Telegram Bot (`apps/telegram`)

- `src/settings.py`: Pydantic settings for bot configuration
- `src/webapp.py`: Command handlers
  - `/start`: Welcome message
  - `/app`: Web App button with inline keyboard
- `src/bot.py`: Main bot entry point with polling mode
- `requirements.txt`: python-telegram-bot 21.9
- Dockerfile: Python 3.12-slim

### 6. Infrastructure (`infra/`)

#### Docker Compose
- `compose/docker-compose.yml`:
  - PostgreSQL 16 with health checks and persistent volume
  - Redis 7-alpine with health checks
  - API service with dependency management
  - Website service
  - Telegram bot service
  - Volume management (postgres_data, redis_data, tts_data)
  - Environment variable injection

#### Environment Configuration
- `compose/env.example`: All required environment variables with placeholders
  - LLM configuration (provider, API key)
  - TTS configuration (provider, API key, voice preset)
  - Telegram bot (token, username, Web App URL)
  - API configuration (host, port, CORS origin)
  - Database credentials
  - Redis URL
  - JWT secret and TTL

#### Helper Scripts
- `scripts/make.ps1`: PowerShell helper for Docker Compose operations
  - Commands: up, down, build, logs, restart, clean
  - Interactive confirmation for destructive operations
- `scripts/make.sh`: Bash equivalent for Linux/macOS

### 7. CI/CD Pipeline (`.github/workflows/ci-cd.yml`)

- Matrix build strategy for api, website, telegram services
- Docker Buildx with layer caching (GitHub Actions cache)
- Push to GitHub Container Registry (GHCR) with SHA and latest tags
- SSH-based deployment to Ubuntu VM
- Automatic `docker compose pull && up -d` on main branch push
- Manual workflow dispatch support
- Pinned action versions (checkout@v4.1.1, build-push-action@v5.1.0, etc.)

### 8. Documentation

- `README.md`: Comprehensive documentation with:
  - Windows PowerShell-first instructions
  - Quick start guide
  - Service endpoints and API routes
  - Telegram bot setup with BotFather steps
  - Development commands (Docker, local, manual)
  - Production deployment guide for Ubuntu VM
  - GitHub secrets configuration
  - Security checklist
  - Database backup/restore commands
  - Troubleshooting section
  - Project structure details
  - Tech stack version table
  - Customization guides (LLM, TTS providers)

### 9. Docker Configuration

- Root `.dockerignore`: Workspace-wide exclusions
- Per-service `.dockerignore` files for optimized build contexts
- Multi-stage builds where applicable (website)
- Pinned base images (python:3.12-slim, node:20-alpine)
- Optimized layer ordering (dependencies before source)

## Follow-up TODOs (Post-MVP)

1. **LLM Integration**: Replace `StubLLMProvider` with OpenAI, Anthropic, or other real LLM
2. **TTS Integration**: Replace `StubTTSProvider` with ElevenLabs, Google TTS, or Azure TTS
3. **Rate Limiting**: Implement Redis-based rate limiter for `/chat` endpoint
4. **User Authentication**: Add proper user management beyond Telegram
5. **Conversation History**: Add UI for viewing past conversations
6. **Advanced RAG**: Integrate vector database for context retrieval
7. **Monitoring**: Add Prometheus metrics and Grafana dashboards
8. **Error Handling**: Enhanced error recovery and user-facing error messages

## Technical Highlights

- **Type Safety**: Full TypeScript types shared between packages
- **Async/Await**: Fully async backend with asyncpg and ASGI
- **Streaming**: Word-by-word streaming over WebSocket
- **Security**: HMAC verification, JWT tokens, CORS configuration
- **Extensibility**: Provider interfaces for LLM and TTS services
- **Observability**: Structured logging throughout
- **Reproducibility**: Pinned versions for all dependencies
- **Developer Experience**: Helper scripts, comprehensive docs, clear structure

## Breaking Changes

N/A - Initial release

## Known Issues

1. Website Dockerfile builds entire monorepo (could be optimized with better context)
2. TTS stub generates simple beeps (not actual speech synthesis)
3. LLM stub echoes with minimal transformation
4. No rate limiting implemented yet
5. No metrics/monitoring built-in

