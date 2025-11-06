# Bot Language-First Flow Implementation - Changelog

## Summary
Implemented language selection flow on `/start` command. Users now see language selection (RU/EN) before the main menu if they haven't chosen a language yet. Language preference is stored in session and persistent storage.

## Changes

### 1. Locale Files (`apps/miniapp_bot/locales/`)

#### `en.json`
- Added `language.choose`: "Choose your language:"
- Added `language.changed`: "Language updated to English."
- Removed `buttons.skills` and `buttons.statuses` (cleanup)

#### `ru.json`
- Added `language.choose`: "Выберите язык:"
- Added `language.changed`: "Язык изменён на русский."
- Removed `buttons.skills` and `buttons.statuses` (cleanup)

### 2. Main Bot File (`apps/miniapp_bot/main.py`)

#### Added Functions
- `language_menu()`: Creates inline keyboard with RU/EN language selection buttons

#### Updated Handlers

**`/start` command handler:**
- Now checks if user has a stored language preference (`bot_state.get_lang()`)
- If no language is stored, shows language selection menu
- If language is stored, immediately shows main menu
- Language is stored in both session (`session.lang`) and persistent storage (`bot_state`)

**`/language` command handler:**
- Always shows language selection menu (allows users to change language at any time)

#### New Handler
- `on_language_callback()`: Handles `set_lang:ru` and `set_lang:en` callback queries
  - Saves language to session and persistent storage
  - Edits the language selection message to show confirmation
  - Sends main menu with selected language

#### Cleanup
- Removed unused import `hbold` from `aiogram.utils.markdown`

### 3. Session Management
- Language is stored in:
  - In-memory session: `session.lang` (for current session)
  - Persistent storage: `bot_state.set_lang()` (survives bot restarts)
- Session state is checked on `/start` to determine if language selection is needed

## Behavior

### New Users
1. User sends `/start`
2. Bot shows language selection (RU/EN inline buttons)
3. User selects language
4. Bot saves language and shows main menu (Open MiniApp, Book a call, Brief)

### Returning Users
1. User sends `/start`
2. Bot immediately shows main menu in their preferred language

### Language Change
1. User sends `/language`
2. Bot shows language selection
3. User selects new language
4. Bot updates language and shows main menu

## Technical Details

### Language Storage
- **Session**: `_sessions[user_id].lang` (in-memory, lost on restart)
- **Persistent**: `UserStateStore.get_lang(user_id)` (persisted to `/data/state/users.json`)

### Language Resolution
- On `/start` without stored language, uses Telegram profile language or default
- Language selection is validated against `SUPPORTED_LANGS` environment variable

### Callback Handling
- Callback data format: `set_lang:ru` or `set_lang:en`
- Handler validates language code and falls back to default if invalid
- Gracefully handles message edit failures (sends new message as fallback)

## Files Modified
1. `apps/miniapp_bot/locales/en.json`
2. `apps/miniapp_bot/locales/ru.json`
3. `apps/miniapp_bot/main.py`

## Testing Checklist
- [ ] New user sees language selection on `/start`
- [ ] Language selection saves preference
- [ ] Main menu appears after language selection
- [ ] Returning user sees main menu immediately
- [ ] `/language` command shows language selection
- [ ] Language change updates menu language
- [ ] Skills/Statuses are not shown anywhere
- [ ] All three main menu buttons work (Open MiniApp, Book a call, Brief)

## Notes
- Skills/Statuses handlers were already removed (confirmed in code comments)
- No new dependencies added
- No folder structure changes
- Uses existing i18n system
- Compatible with existing session management

