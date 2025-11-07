# Mini App Bot

Aiogram-based Telegram bot that exposes the AI Avatar miniapp through a two-button inline keyboard.

## Quick Menu

- `TELEGRAM_MINIAPP_URL` — HTTPS link to the Telegram WebApp. Button label: “Открыть миниап”.
- `TELEGRAM_BOOKING_URL` — External scheduling link (Cal.com, Calendly, etc.). Button label: “Записаться”.
- Missing or empty values hide the corresponding button after logging a warning; the bot keeps running.
- Text commands `/skills`, `/status`, `/tz` and their Russian equivalents now reply with a short hint plus the same two-button inline keyboard.

## Menu Diagnostics

- Required envs: `TELEGRAM_MINIAPP_URL`, `TELEGRAM_BOOKING_URL` (omit one to hide its button after a warning).
- `/menu` — resend the localized inline menu built from the current env values.
- `/debug_menu` — respond with `{"miniapp_url": "set|empty", "booking_url": "set|empty", "locale": "ru|en"}` and attach the same menu.
- Testing: set the envs, restart the bot, run `/start`, switch language, then use `/menu` and `/debug_menu` to verify buttons and diagnostics.

## Setup

### 1. Create the bot

Use [@BotFather](https://t.me/BotFather) to create a bot and obtain the token.

### 2. Configure environment

Add the variables to `.env.miniapp` (or the runtime env file used by Docker Compose):

```env
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_NAME=YourBotName
DEFAULT_LANG=ru
SUPPORTED_LANGS=ru,en
TELEGRAM_MINIAPP_URL=https://your-miniapp-host/miniapp
TELEGRAM_BOOKING_URL=https://cal.com/your-team/intro-call
```

Only the two `TELEGRAM_*_URL` values control the inline menu. Leave either blank to hide that button (a warning is logged at startup).

### 3. Run locally

```bash
pip install -r requirements.txt
python -m apps.miniapp_bot.main
```

The bot defaults to long polling. Set `BOT_MODE=webhook` and `WEBHOOK_URL` if you later configure webhooks.

## Behaviour

- `/start` prompts for language (reply keyboard) and then shows the inline menu.
- The quick menu is always rendered inline; reply keyboards are not used for external links.
- If users manually type legacy commands (`/skills`, “Навыки”, `/tz`, etc.), they are guided back to the two primary actions with the same inline buttons.
- Brief upload, admin forwarding, and Notion logging stay available via existing handlers when enabled.

## Dependencies

- aiogram==3.7.0
- pydantic>=2.4.1,<2.8
- python-dotenv==1.0.1
- httpx==0.27.2 (for optional integrations)

## Troubleshooting

- **No buttons shown:** Check `TELEGRAM_MINIAPP_URL` / `TELEGRAM_BOOKING_URL` are set and publicly accessible (HTTPS).
- **WebApp fails to open:** The URL must match a domain configured via BotFather `/setdomain` and resolve over HTTPS.
- **Booking link hidden:** A warning `menu.button.booking.disabled` at startup indicates the env var was missing or blank.

Run only one polling instance at a time; multiple pollers will conflict.

