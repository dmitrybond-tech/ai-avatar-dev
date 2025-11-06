# Bot Language-First Flow - Unified Diffs

## A) Locale Files

### `apps/miniapp_bot/locales/en.json`

```diff
 {
   "start": {
     "choose_language": "Choose your language",
     "confirm_language": "Language set to English"
   },
   "menu": {
     "openMiniApp": "Open MiniApp",
     "bookCall": "Book a call",
     "brief": "Brief for Estimate"
   },
   "messages": {
     "main": "Choose an action:"
   },
+  "language": {
+    "choose": "Choose your language:",
+    "changed": "Language updated to English."
+  },
   "buttons": {
     "language": "Language",
     "brief": "📎 Brief for estimate",
     "open_app": "Open MiniApp",
-    "book": "Book a call",
-    "skills": "Skills",
-    "statuses": "Statuses"
+    "book": "Book a call"
   },
   "brief": {
     "prompt_upload": "Please attach a file (document/photo) and optional text.",
     "received": "Thanks! Your brief was sent for review."
   },
   "errors": {
     "try_again": "Something went wrong. Please try again later."
   }
 }
```

### `apps/miniapp_bot/locales/ru.json`

```diff
 {
   "start": {
     "choose_language": "Выберите язык",
     "confirm_language": "Язык установлен: Русский"
   },
   "menu": {
     "openMiniApp": "Открыть мини-приложение",
     "bookCall": "Назначить звонок",
     "brief": "Бриф на оценку"
   },
   "messages": {
     "main": "Выберите действие:"
   },
+  "language": {
+    "choose": "Выберите язык:",
+    "changed": "Язык изменён на русский."
+  },
   "buttons": {
     "language": "Язык",
     "brief": "📎 ТЗ на оценку",
     "open_app": "Открыть MiniApp",
-    "book": "Записаться",
-    "skills": "Навыки",
-    "statuses": "Статусы"
+    "book": "Записаться"
   },
   "brief": {
     "prompt_upload": "Прикрепите файл (документ/фото) и при желании текст.",
     "received": "Спасибо! Ваше ТЗ отправлено на оценку."
   },
   "errors": {
     "try_again": "Что-то пошло не так. Попробуйте позже."
   }
 }
```

## B) Main Bot File

### `apps/miniapp_bot/main.py`

#### Imports (cleanup)

```diff
 from aiogram.client.default import DefaultBotProperties
-from aiogram.utils.markdown import hbold
 from pydantic import BaseModel
```

#### Added Language Menu Function

```diff
 def main_menu(lang: str) -> InlineKeyboardMarkup:
     rows = [
         [InlineKeyboardButton(text=i18n.t(lang, "menu.openMiniApp"), web_app=WebAppInfo(url=MINIAPP_URL))],
         [InlineKeyboardButton(text=i18n.t(lang, "menu.bookCall"), url=CAL_URL)],
         [InlineKeyboardButton(text=i18n.t(lang, "menu.brief"), url=BRIEF_URL or "https://example.com")],
     ]
     return InlineKeyboardMarkup(inline_keyboard=rows)
 
+
+def language_menu() -> InlineKeyboardMarkup:
+    """Create inline keyboard for language selection."""
+    rows = [
+        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru")],
+        [InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en")],
+    ]
+    return InlineKeyboardMarkup(inline_keyboard=rows)
```

#### Updated /start Handler

```diff
 @dp.message(CommandStart())
 async def cmd_start(message: Message) -> None:
-    """Handle /start: detect locale and show main inline menu."""
+    """Handle /start: show language selection if no locale, otherwise show main menu."""
     user_id = message.from_user.id if message.from_user else 0
-    profile_lang = (message.from_user.language_code if message.from_user else None) or None
     session = get_session(user_id)
     stored = bot_state.get_lang(user_id)
-    lang = i18n.resolve_lang(user_id, stored, profile_lang)
-    session.lang = lang
-    await message.answer(i18n.t(lang, "messages.main"), reply_markup=main_menu(lang))
+    
+    # Check if user has explicitly chosen a language (stored in persistent state)
+    if not stored:
+        # No language chosen yet - show language selection
+        # Use a default language for the "choose language" message itself
+        profile_lang = (message.from_user.language_code if message.from_user else None) or None
+        default_lang = i18n.resolve_lang(user_id, None, profile_lang)
+        await message.answer(i18n.t(default_lang, "language.choose"), reply_markup=language_menu())
+        return
+    
+    # Language is set - show main menu
+    session.lang = stored
+    await message.answer(i18n.t(session.lang, "messages.main"), reply_markup=main_menu(session.lang))
```

#### Updated /language Handler

```diff
 @dp.message(Command("language"))
 async def cmd_language(message: Message) -> None:
-    # Retain command but respond with current menu
+    """Handle /language: always show language selection."""
     user_id = message.from_user.id if message.from_user else 0
     session = get_session(user_id)
-    await message.answer(i18n.t(session.lang, "messages.main"), reply_markup=main_menu(session.lang))
+    # Use current session language or default for the "choose language" message
+    lang = session.lang or DEFAULT_LANG
+    await message.answer(i18n.t(lang, "language.choose"), reply_markup=language_menu())
```

#### Removed Old Language Handler, Added New Callback Handler

```diff
-@dp.message(F.text.in_({"Русский", "English"}))
-async def on_language_choice(message: Message) -> None:
-    user_id = message.from_user.id if message.from_user else 0
-    session = get_session(user_id)
-    choice = (message.text or "").lower()
-    lang = "ru" if "рус" in choice else "en"
-    # validate against supported langs
-    if lang not in set(SUPPORTED_LANGS.split(",")):
-        lang = DEFAULT_LANG
-    bot_state.set_lang(user_id, lang)
-    session.lang = lang
-    await message.answer(i18n.t(lang, "start.confirm_language"), reply_markup=_main_keyboard(lang))
+
+@dp.callback_query(F.data.startswith("set_lang:"))
+async def on_language_callback(callback: CallbackQuery) -> None:
+    """Handle language selection callback."""
+    user_id = callback.from_user.id if callback.from_user else 0
+    lang_code = callback.data.split(":")[1] if ":" in callback.data else DEFAULT_LANG
+    
+    # Validate language
+    if lang_code not in set(SUPPORTED_LANGS.split(",")):
+        lang_code = DEFAULT_LANG
+    
+    # Save language to session and persistent storage
+    session = get_session(user_id)
+    session.lang = lang_code
+    bot_state.set_lang(user_id, lang_code)
+    
+    # Answer callback query
+    await callback.answer()
+    
+    # Try to edit the message, fallback to new message if edit fails
+    if callback.message:
+        try:
+            await callback.message.edit_text(i18n.t(lang_code, "language.changed"))
+        except Exception:
+            # If edit fails, send a new message
+            await callback.message.answer(i18n.t(lang_code, "language.changed"))
+        
+        # Send main menu
+        await callback.message.answer(i18n.t(lang_code, "messages.main"), reply_markup=main_menu(lang_code))
```

## Summary

### Files Modified
1. `apps/miniapp_bot/locales/en.json` - Added language keys, removed Skills/Statuses
2. `apps/miniapp_bot/locales/ru.json` - Added language keys, removed Skills/Statuses  
3. `apps/miniapp_bot/main.py` - Added language menu, updated handlers, added callback handler

### Key Changes
- Language selection shown on `/start` if no language preference exists
- Language stored in session and persistent storage
- `/language` command always shows language selection
- Inline callback handler for language selection (`set_lang:ru` / `set_lang:en`)
- Removed Skills/Statuses from locale files
- Removed unused import

### Behavior
- **New users**: See language selection → choose language → see main menu
- **Returning users**: See main menu immediately in their preferred language
- **Language change**: Use `/language` command to change language anytime

