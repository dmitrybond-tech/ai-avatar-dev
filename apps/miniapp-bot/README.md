# Mini App Bot

Telegram bot that opens the Mini App WebApp using a reply keyboard button.

## Features

- **Long Polling**: No webhook setup required (perfect for MVP/development)
- **WebApp Button**: One-tap access to the Mini App interface
- **Simple & Minimal**: Single file, clear logic

## Setup

### 1. Create Telegram Bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram:

```
/newbot
# Follow prompts to choose name and username
# Copy the token provided
```

### 2. Configure Bot

Add the token to your `.env.miniapp`:

```env
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_NAME=YourBotName
WEBAPP_URL=http://localhost:5173/miniapp/
```

**Important Notes:**
- `WEBAPP_URL` must be publicly accessible for production use (use ngrok/cloudflare tunnel for local testing with real Telegram)
- For local development, you can test the API separately and use a deployed frontend URL
- In production, set `WEBAPP_URL` to your deployed frontend (e.g., `https://yourdomain.com/miniapp/`)

### 3. Run Bot

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python bot.py
```

## Bot Commands

- `/start` - Show welcome message with WebApp button

## How It Works

1. User sends `/start` command
2. Bot responds with a ReplyKeyboard containing a WebApp button
3. User taps "🤖 Open Assistant" button
4. Telegram opens the Mini App WebApp in-app browser
5. User interacts with the chat interface

## Development vs Production

### Development (Long Polling)
✅ Current setup - perfect for local development
- No server setup needed
- Bot pulls messages from Telegram
- Easy to debug

### Production (Webhooks - Future)
When scaling, consider webhooks:
- More efficient at scale
- Requires HTTPS endpoint
- Instant message delivery

For MVP, long polling is recommended (current setup).

## Docker

```bash
# Build
docker build -t miniapp-bot .

# Run
docker run --env-file .env.miniapp miniapp-bot
```

## Dependencies

- python-telegram-bot==21.4
- python-dotenv==1.0.1

## Troubleshooting

**Bot doesn't respond:**
- Check `TELEGRAM_TOKEN` is correct
- Ensure bot is not blocked by user
- Check logs for errors

**WebApp doesn't open:**
- Verify `WEBAPP_URL` is publicly accessible
- Check URL format (must include protocol: http:// or https://)
- For production, WebApp URL must use HTTPS

**Multiple instances running:**
- Only one bot instance can poll at a time
- Stop other instances or use webhooks for multiple servers

