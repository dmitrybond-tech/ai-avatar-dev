*** Add File: apps/miniapp-api/requirements.txt
fastapi==0.115.2
uvicorn==0.31.1
pydantic==2.9.2
PyYAML==6.0.2

*** Add File: apps/miniapp-api/rules.yaml
version: 1
languages: [ru, en]
labels:
  start:
    ru: "Старт"
    en: "Start"
  back:
    ru: "Назад"
    en: "Back"
  language:
    ru: "Язык"
    en: "Language"
  book:
    ru: "Записаться"
    en: "Book a call"
  about:
    ru: "Обо мне"
    en: "About"
  services:
    ru: "Услуги"
    en: "Services"
  cases:
    ru: "Кейсы"
    en: "Cases"
intents:
  - key: start
    ru: ["старт", "начать"]
    en: ["start", "hi", "hello"]
  - key: book
    ru: ["записаться", "созвон", "встреча"]
    en: ["book", "call", "meeting"]
  - key: about
    ru: ["обо мне", "кто ты"]
    en: ["about", "bio", "who are you"]
  - key: services
    ru: ["услуги", "что умеешь"]
    en: ["services", "what you do"]
  - key: cases
    ru: ["кейсы", "проекты"]
    en: ["cases", "projects"]
scenes:
  start:
    text:
      ru: "Привет! Я ассистент Дмитрия. Чем помочь?"
      en: "Hi! I’m Dmitry’s assistant. How can I help?"
    buttons: [book, about, services, cases]
  about:
    text:
      ru: "8+ лет в облаках (Azure/AWS/GCP), SaaS/маркетплейсы, консалтинг."
      en: "8+ years in cloud (Azure/AWS/GCP), SaaS/marketplaces, consulting."
    buttons: [book, services, cases, start]
  services:
    text:
      ru: "- Аудит и миграции\n- Модернизация\n- Безопасность\n- PM/Delivery"
      en: "- Audits & migrations\n- Modernization\n- Security\n- PM/Delivery"
    buttons: [book, cases, start]
  cases:
    text:
      ru: "CloudBlue, Datacom, NCE, SSO, микросервисы, 5x9, и пр."
      en: "CloudBlue, Datacom, NCE, SSO, microservices, 5x9, etc."
    buttons: [book, services, start]

*** Add File: apps/miniapp-api/main.py
[see repository for full file contents; FastAPI app with /healthz, /rules, /cal/suggest]

*** Add File: apps/miniapp-bot/requirements.txt
aiogram==3.13.1
pydantic==2.9.2
python-dotenv==1.0.1
httpx==0.27.2
uvloop==0.21.0

*** Add File: apps/miniapp-bot/main.py
[see repository for full file contents; aiogram v3 bot with scenes, callbacks, WebApp button]

*** Add File: apps/miniapp-web/package.json
{ pinned dependencies and scripts }

*** Add File: apps/miniapp-web/index.html
<!doctype html>
<html lang="en"> ... </html>

*** Add File: apps/miniapp-web/tsconfig.json
{ TypeScript config }

*** Add File: apps/miniapp-web/tailwind.config.js
export default { content: ["./index.html", "./src/**/*.{ts,tsx}"] }

*** Add File: apps/miniapp-web/postcss.config.js
export default { plugins: { tailwindcss: {}, autoprefixer: {} } }

*** Add File: apps/miniapp-web/vite.config.ts
import { defineConfig } from 'vite' ...

*** Add File: apps/miniapp-web/src/main.tsx
import React from 'react' ...

*** Add File: apps/miniapp-web/src/App.tsx
React component fetching /rules, rendering buttons, toggling language, opening Cal URL

*** Add File: apps/miniapp-web/src/index.css
@tailwind base; @tailwind components; @tailwind utilities; ...

*** Add File: apps/miniapp-web/src/vite-env.d.ts
Telegram WebApp types shim

*** Add File: dev.ps1
PowerShell script with tasks: bot, api, web

*** Add File: infra/compose/miniapp.compose.yaml
Compose services: api, bot, web with ports 8080 and 5173

*** Add File: README-miniapp.md
Windows-first documentation and BotFather setup
