# CSV Skills Mode Stability - Changelog

## Overview
Улучшена стабильность CSV-режима навыков: гарантирован fallback при сбоях CSV, запрещены вызовы Notion в CSV-режиме, улучшен debug endpoint, исправлены сообщения в FE.

## Changes

### 1. CSV Loader (`apps/miniapp-api/app/services/skills_loader.py`)

#### 1.1 Улучшена нормализация заголовков CSV
- Обновлены алиасы заголовков для точного соответствия формату CSV (Title EN, Bullets EN, etc.)
- Приоритет отдан вариантам с пробелами ("title en" перед "title_en") для совместимости
- Улучшена обработка NaN/None значений: все конвертируются в пустые строки

#### 1.2 Улучшена обработка данных
- Добавлен `.strip()` при нормализации ключей заголовков
- Улучшена обработка значений: все NaN/None конвертируются в пустые строки
- Добавлено debug-логирование для пропущенных строк без заголовков

**Impact**: CSV loader теперь более устойчив к вариациям формата и ошибкам данных.

---

### 2. Skills Router (`apps/miniapp-api/routers/skills.py`)

#### 2.1 Гарантирован fallback при пустом CSV
- `_load_skills_with_fallback()` теперь всегда возвращает непустой список в CSV-режиме
- Добавлена обработка исключений: при любой ошибке CSV возвращается fallback
- В `_list_skills_impl()` добавлен последний резервный fallback на случай пустого списка

#### 2.2 Строгий запрет вызовов Notion в CSV-режиме
- Все функции (`_list_skills_impl`, `_get_skill_impl`, `search_skills_api`, `ask_skills`) проверяют `SKILLS_SOURCE=csv`
- В CSV-режиме НИКОГДА не вызывается `_repo(request)` (который может обращаться к Notion)
- Добавлены комментарии в коде для ясности

#### 2.3 Улучшен debug endpoint (`/api/skills/debug`)
- Добавлено поле `csv_exists` для проверки существования файла
- Улучшена обработка ошибок: все ошибки собираются в массив `errors`
- В CSV-режиме гарантированно не вызывается Notion (даже для проверки)
- Улучшена структура ответа: `sample` содержит первые 1-2 записи

**Impact**: 
- FE никогда не получит пустой список навыков в CSV-режиме
- В логах не будет запросов к Notion при `SKILLS_SOURCE=csv`
- Debug endpoint предоставляет полную диагностику состояния CSV

---

### 3. Frontend (`apps/miniapp-web/src/pages/SkillsPage.tsx`)

#### 3.1 Исправлено сообщение об отсутствии навыков
- Изменено сообщение с "No skills are published yet" на "No skills available yet"
- Убрана ссылка на концепцию "published", которая не применима к CSV-режиму

**Impact**: Сообщения в UI теперь корректны для CSV-режима.

---

### 4. Кнопка "Очистить чат" в Telegram WebApp

#### 4.1 Проверка видимости
- Кнопка уже была видна в Telegram WebApp (нет условий `if (!isTelegram)`)
- Кнопка рендерится всегда, когда есть сообщения пользователя (`!hasUserMessages`)

**Impact**: Кнопка "Очистить чат" доступна и в Telegram WebApp, и в обычной веб-версии.

---

## Testing Checklist

- [ ] `/api/skills?lang=en` возвращает >0 элементов в CSV-режиме
- [ ] При сломанном CSV возвращается fallback с >0 элементов
- [ ] `/api/skills/debug` показывает `source: "csv"` или `source: "fallback"`, `count>0`
- [ ] `/api/skills/debug` содержит поля: `csv_exists`, `csv_ok`, `errors`, `sample`
- [ ] FE отрисовывает тайлы без фильтрации по "published"
- [ ] Кнопка "Очистить чат" видна в Telegram WebApp
- [ ] В логах нет запросов к Notion при `SKILLS_SOURCE=csv`

---

## Files Modified

1. `apps/miniapp-api/app/services/skills_loader.py` - улучшена обработка CSV
2. `apps/miniapp-api/routers/skills.py` - гарантирован fallback, запрещены вызовы Notion
3. `apps/miniapp-web/src/pages/SkillsPage.tsx` - исправлено сообщение

---

## Backward Compatibility

✅ Все изменения обратно совместимы:
- Не изменены API endpoints
- Не изменены форматы ответов
- Не изменены базовые пути/роутинги
- Fallback уже существовал, теперь просто гарантирован

---

## Deployment Notes

1. Убедитесь, что `SKILLS_SOURCE=csv` установлен в env
2. Убедитесь, что `SKILLS_CSV_PATH=/app/data/skills.csv` установлен
3. Убедитесь, что volume mount настроен: `../../apps/miniapp-api/data:/app/data:ro`
4. После деплоя проверьте `/api/skills/debug` для диагностики

