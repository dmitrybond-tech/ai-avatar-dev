# MiniApp Localization & Brief Upload Feature - Changelog

## Summary
Implemented full localization (RU/EN) for the mini-app header and buttons, plus a brief upload feature that saves files to the server and forwards them to Telegram admin.

## Changes

### 1. Bot: Language Parameter in Web App URL
**File**: `apps/miniapp_bot/main.py`
- Modified `main_menu()` function to add `?lang=<locale>` parameter to the web_app URL
- Uses `urllib.parse` to properly construct URL with query parameters
- Language is taken from the session's `lang` field

### 2. Mini-App: i18n System
**New Files**:
- `apps/miniapp-web/src/i18n/en.json` - English translations
- `apps/miniapp-web/src/i18n/ru.json` - Russian translations
- `apps/miniapp-web/src/lib/i18n.ts` - i18n helper with locale detection

**Features**:
- Locale detection priority:
  1. URLSearchParams (`?lang=ru|en`)
  2. Telegram WebApp `initDataUnsafe.user.language_code` (ru → ru, else → en)
  3. localStorage
  4. navigator.language
- Simple i18n helper without external dependencies
- `createI18n()` function returns `{ t, get, set }` interface

### 3. Mini-App: Header Localization
**File**: `apps/miniapp-web/src/App.tsx`
- Updated header to use `i18n.t('header.title')` for localized title
- Added "Personal site" button linking to `https://dmitrybond.tech`
- Button opens in new tab with proper security attributes
- Header layout adjusted to accommodate new button

### 4. Mini-App: Brief Upload Modal
**New File**: `apps/miniapp-web/src/components/BriefUploadModal.tsx`
- Modal component for file upload
- File input with accept attribute for allowed extensions
- POST request to `/briefs/upload` with FormData (file + locale)
- Success/error handling with Telegram WebApp popup (fallback to alert)
- Loading state during upload
- Closes modal after successful upload

### 5. Mini-App: Buttons Localization
**File**: `apps/miniapp-web/src/components/Buttons.tsx`
- All buttons now use i18n translations:
  - "Book a call" → `i18n.t('actions.bookCall')`
  - "Brief for Estimate" → `i18n.t('actions.brief')`
  - "What I can do?" → `i18n.t('actions.whatICanDo')`
  - "Task status" → `i18n.t('actions.taskStatus')`
- Integrated `BriefUploadModal` component
- Brief button opens upload modal on click

### 6. API: Brief Upload Router
**New File**: `apps/miniapp-api/routers/briefs.py`
- POST `/briefs/upload` endpoint
- Accepts `multipart/form-data` with `file` and optional `locale`
- File validation:
  - Extension check against `ALLOWED_EXT` env var
  - Size check (streaming) against `MAX_UPLOAD_MB` env var
- File storage:
  - Saves to `${UPLOAD_DIR}/${timestamp}_${sanitized_name}`
  - Filename sanitization for security
- Telegram forwarding:
  - Sends document to admin chat via Telegram Bot API
  - Caption includes locale, filename, and size
  - Non-blocking: API doesn't fail if Telegram send fails
- Returns JSON with upload status

**File**: `apps/miniapp-api/main.py`
- Added import and registration of briefs router

### 7. API: Dependencies
**File**: `apps/miniapp-api/requirements.txt`
- `httpx>=0.27.0` already present (no change needed)

### 8. Docker Compose: Environment & Volumes
**File**: `infra/compose/miniapp.final.override.yml`
- Added environment variables:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_ADMIN_CHAT_ID`
  - `UPLOAD_DIR=/app/uploads/briefs`
  - `MAX_UPLOAD_MB` (default: 25)
  - `ALLOWED_EXT` (default: pdf,doc,docx,txt,png,jpg,jpeg,zip)
- Added volume mount: `./data/uploads:/app/uploads`

### 9. Environment Configuration
**File**: `infra/compose/env.miniapp.example`
- Added documentation for brief upload configuration:
  - `TELEGRAM_BOT_TOKEN` (required)
  - `TELEGRAM_ADMIN_CHAT_ID` (required)
  - `MAX_UPLOAD_MB` (optional, default: 25)
  - `ALLOWED_EXT` (optional, default: pdf,doc,docx,txt,png,jpg,jpeg,zip)

## Translation Keys

### English (`en.json`)
- `header.title`: "Dmitry's Assistant"
- `header.personalSite`: "Personal website"
- `actions.bookCall`: "Book a call"
- `actions.brief`: "Brief for Estimate"
- `actions.whatICanDo`: "What I can do?"
- `actions.taskStatus`: "Task status"
- `brief.title`: "Upload brief for estimate"
- `brief.chooseFile`: "Choose a file"
- `brief.send`: "Send"
- `brief.cancel`: "Cancel"
- `brief.success`: "Your file has been sent. We'll get back to you soon."
- `brief.error`: "Upload failed. Please try again."

### Russian (`ru.json`)
- `header.title`: "Ассистент Дмитрия"
- `header.personalSite`: "Личный сайт"
- `actions.bookCall`: "Назначить звонок"
- `actions.brief`: "Загрузить ТЗ на оценку"
- `actions.whatICanDo`: "Что я умею?"
- `actions.taskStatus`: "Статус задач"
- `brief.title`: "Загрузка ТЗ на оценку"
- `brief.chooseFile`: "Выберите файл"
- `brief.send`: "Отправить"
- `brief.cancel`: "Отмена"
- `brief.success`: "Файл отправлен. Мы свяжемся с вами в ближайшее время."
- `brief.error`: "Не удалось загрузить файл. Попробуйте ещё раз."

## Technical Notes

1. **No npm dependencies added** - i18n system is custom-built
2. **httpx already present** - no new Python dependencies needed
3. **File upload security**:
   - Extension whitelist
   - Size limit with streaming check
   - Filename sanitization
4. **Telegram integration**:
   - Uses Telegram Bot API `sendDocument` endpoint
   - Non-blocking: API continues even if Telegram fails
   - Caption includes metadata (locale, size)
5. **Locale detection**:
   - URL parameter takes highest priority
   - Falls back to Telegram user language
   - Persists in localStorage
   - Final fallback to browser language

## Testing Checklist

- [ ] Bot adds `?lang=ru` or `?lang=en` to web_app URL
- [ ] Mini-app detects locale from URL and displays correct language
- [ ] Header shows "Ассистент Дмитрия" in RU, "Dmitry's Assistant" in EN
- [ ] "Personal site" button appears and links to https://dmitrybond.tech
- [ ] All buttons are localized correctly
- [ ] Brief upload modal opens on button click
- [ ] File upload works with valid files
- [ ] File size limit is enforced
- [ ] File extension validation works
- [ ] Success popup appears after upload
- [ ] File is saved to `./data/uploads/briefs/`
- [ ] File is forwarded to Telegram admin chat
- [ ] Error handling works for invalid files

## Deployment Notes

1. Ensure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ADMIN_CHAT_ID` are set in `.env.miniapp`
2. Create `./data/uploads` directory (or ensure it exists)
3. Rebuild API container to include briefs router
4. Restart services: `api`, `bot`, `web`

