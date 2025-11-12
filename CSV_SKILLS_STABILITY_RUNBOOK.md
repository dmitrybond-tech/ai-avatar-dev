# CSV Skills Mode Stability - Runbook

## Prerequisites

- Docker Compose V2
- Access to miniapp-api container
- `SKILLS_SOURCE=csv` в environment
- CSV файл по пути `SKILLS_CSV_PATH` (по умолчанию `/app/data/skills.csv`)

---

## Step 1: Проверка Docker Compose конфигурации

### 1.1 Проверка env переменных

```bash
cd infra/compose
docker compose --env-file .env.miniapp -f miniapp.compose.yaml config | grep -A 5 SKILLS
```

**Ожидаемый результат:**
```
SKILLS_SOURCE: csv
SKILLS_CSV_PATH: /app/data/skills.csv
```

### 1.2 Проверка volume mount

```bash
docker compose --env-file .env.miniapp -f miniapp.compose.yaml config | grep -A 3 volumes -A 3 api
```

**Ожидаемый результат:**
```
volumes:
  - ../../apps/miniapp-api/data:/app/data:ro
```

**Если volume не настроен**, добавьте в `miniapp.csv.override.yml`:
```yaml
services:
  api:
    volumes:
      - ../../apps/miniapp-api/data:/app/data:ro
```

---

## Step 2: Проверка наличия CSV файла в контейнере

### 2.1 Проверка существования файла

```bash
docker compose --env-file .env.miniapp -f miniapp.compose.yaml exec api ls -la /app/data/skills.csv
```

**Ожидаемый результат:**
```
-rw-r--r-- 1 root root 1234 Jan 1 12:00 /app/data/skills.csv
```

### 2.2 Просмотр первых строк CSV

```bash
docker compose --env-file .env.miniapp -f miniapp.compose.yaml exec api head -5 /app/data/skills.csv
```

**Ожидаемый результат:**
```
Title EN,Bullets EN,Bullets RU,Examples EN,Examples RU,Short EN,Short RU,Slug,Tags,Title RU
Automation,"Build ETL/ELT pipelines...
...
```

---

## Step 3: Проверка API endpoints

### 3.1 Проверка списка навыков

```bash
curl -s http://localhost:18080/api/skills?lang=en | jq 'length'
```

**Ожидаемый результат:** `> 0` (например, `7`)

**Если результат `0`:**
1. Проверьте логи: `docker compose logs api | grep -i csv`
2. Проверьте debug endpoint (см. шаг 3.2)

### 3.2 Проверка debug endpoint

```bash
curl -s http://localhost:18080/api/skills/debug | jq .
```

**Ожидаемый результат:**
```json
{
  "source": "csv",
  "count": 7,
  "csv_path": "/app/data/skills.csv",
  "csv_exists": true,
  "csv_ok": true,
  "errors": null,
  "sample": [
    {
      "slug": "automation",
      "title": "Automation"
    }
  ]
}
```

**Если `source: "fallback"`:**
- CSV файл не загружается корректно
- Проверьте `csv_exists` и `csv_ok`
- Проверьте `errors` для деталей

**Если `count: 0`:**
- Это критическая ошибка - fallback должен вернуть минимум 2-3 навыка
- Проверьте логи и `errors`

### 3.3 Проверка детального endpoint

```bash
curl -s http://localhost:18080/api/skills/automation?lang=en | jq '.bullets | length'
```

**Ожидаемый результат:** `> 0` (например, `5`)

---

## Step 4: Проверка отсутствия вызовов Notion

### 4.1 Проверка логов на наличие запросов к Notion

```bash
docker compose --env-file .env.miniapp -f miniapp.compose.yaml logs api | grep -i notion
```

**Ожидаемый результат:** Нет строк с "notion" (или только предупреждения о том, что Notion не используется)

**Если есть запросы к Notion:**
- Проверьте, что `SKILLS_SOURCE=csv` установлен
- Перезапустите контейнер: `docker compose restart api`
- Проверьте логи снова

### 4.2 Проверка через debug endpoint

```bash
curl -s http://localhost:18080/api/skills/debug | jq '.notion'
```

**В CSV-режиме:** Поле `notion` отсутствует в ответе (только в non-CSV режиме)

---

## Step 5: Проверка Frontend

### 5.1 Проверка Network запросов

1. Откройте DevTools (F12)
2. Перейдите на вкладку Network
3. Откройте страницу `/skills` или `/ru/skills`
4. Найдите запрос к `/api/skills?lang=...`

**Ожидаемый результат:**
- Status: `200`
- Response: непустой массив `[{slug, title, short, tags}, ...]`

### 5.2 Проверка отображения тайлов

**Ожидаемый результат:**
- Видны тайлы навыков (минимум 2-3)
- Нет сообщения "No skills available yet" (если CSV загружен)
- Каждый тайл содержит: заголовок, краткое описание, теги

### 5.3 Проверка кнопки "Очистить чат" в Telegram WebApp

1. Откройте приложение в Telegram WebApp
2. Отправьте несколько сообщений в чат
3. Проверьте наличие кнопки "Очистить чат"

**Ожидаемый результат:**
- Кнопка видна и доступна
- При клике появляется подтверждение
- После подтверждения чат очищается

---

## Step 6: Диагностика проблем

### Проблема: `/api/skills` возвращает пустой массив

**Диагностика:**
```bash
# 1. Проверьте debug endpoint
curl -s http://localhost:18080/api/skills/debug | jq '{source, count, csv_exists, csv_ok, errors}'

# 2. Проверьте логи
docker compose logs api | grep -i "csv\|fallback\|skills" | tail -20

# 3. Проверьте файл в контейнере
docker compose exec api cat /app/data/skills.csv | head -3
```

**Возможные причины:**
1. CSV файл не существует → проверьте volume mount
2. CSV файл пустой → проверьте содержимое файла
3. CSV файл битый → проверьте формат (должен быть UTF-8, правильные заголовки)
4. Fallback не сработал → проверьте логи на ошибки

**Решение:**
- Если `csv_exists: false` → настройте volume mount
- Если `csv_ok: false` → проверьте формат CSV файла
- Если `errors` не пустой → исправьте ошибки из списка

### Проблема: В логах есть запросы к Notion

**Диагностика:**
```bash
# Проверьте env переменную
docker compose exec api env | grep SKILLS_SOURCE
```

**Решение:**
- Убедитесь, что `SKILLS_SOURCE=csv`
- Перезапустите контейнер: `docker compose restart api`
- Проверьте, что используется правильный compose файл с CSV override

### Проблема: Кнопка "Очистить чат" не видна в Telegram

**Диагностика:**
1. Проверьте консоль браузера на ошибки
2. Проверьте, что есть сообщения пользователя (кнопка показывается только если есть история)
3. Проверьте CSS: убедитесь, что нет `display: none` или `visibility: hidden`

**Решение:**
- Кнопка должна быть видна всегда, когда `hasUserMessages === true`
- Если проблема сохраняется, проверьте код компонента `Chat.tsx`

---

## Step 7: Smoke тесты

### Полный smoke test

```bash
# 1. Проверка списка
curl -s http://localhost:18080/api/skills?lang=en | jq 'length' | grep -q "^[1-9]" && echo "✓ List OK" || echo "✗ List FAILED"

# 2. Проверка debug
curl -s http://localhost:18080/api/skills/debug | jq '.count' | grep -q "^[1-9]" && echo "✓ Debug OK" || echo "✗ Debug FAILED"

# 3. Проверка детального endpoint
curl -s http://localhost:18080/api/skills/automation?lang=en | jq '.bullets | length' | grep -q "^[1-9]" && echo "✓ Detail OK" || echo "✗ Detail FAILED"

# 4. Проверка отсутствия Notion (в CSV режиме)
docker compose logs api 2>&1 | grep -i "notion.*query\|notion.*database" | wc -l | grep -q "^0$" && echo "✓ No Notion calls" || echo "✗ Notion calls detected"
```

**Ожидаемый результат:** Все проверки должны пройти (✓)

---

## Команды для быстрой проверки

```bash
# Полная проверка за один раз
cd infra/compose
export COMPOSE_FILE="miniapp.compose.yaml:miniapp.runtime.yml:miniapp.csv.override.yml"

# Проверка конфигурации
docker compose --env-file .env.miniapp config | grep -A 2 SKILLS_SOURCE

# Проверка файла
docker compose --env-file .env.miniapp exec api test -f /app/data/skills.csv && echo "✓ CSV exists" || echo "✗ CSV missing"

# Проверка API
curl -s http://localhost:18080/api/skills/debug | jq '{source, count, csv_exists, csv_ok}'

# Проверка логов
docker compose --env-file .env.miniapp logs api --tail=50 | grep -i "csv\|fallback" | tail -10
```

---

## Acceptance Criteria Checklist

- [ ] `/api/skills?lang=en` возвращает >0 элементов
- [ ] При сломанном CSV возвращается fallback с >0 элементов
- [ ] `/api/skills/debug` показывает `source: "csv"` или `source: "fallback"`, `count>0`
- [ ] `/api/skills/debug` содержит поля: `csv_exists`, `csv_ok`, `errors`, `sample`
- [ ] FE отрисовывает тайлы без фильтрации по "published"
- [ ] Кнопка "Очистить чат" видна в Telegram WebApp
- [ ] В логах нет запросов к Notion при `SKILLS_SOURCE=csv`

---

## Troubleshooting Quick Reference

| Симптом | Причина | Решение |
|---------|---------|---------|
| `count: 0` в debug | CSV не загружается | Проверьте `csv_exists`, `csv_ok`, `errors` |
| `source: "fallback"` | CSV битый или пустой | Исправьте CSV файл или проверьте формат |
| Запросы к Notion | `SKILLS_SOURCE` не установлен | Установите `SKILLS_SOURCE=csv` и перезапустите |
| Кнопка не видна | Нет сообщений пользователя | Отправьте сообщение в чат |
| Пустой список в FE | API возвращает `[]` | Проверьте debug endpoint и логи |

