# Rasa OSS Bot Integration - Changes Summary

## Overview

This document provides a unified diff and numbered changelog for the Rasa OSS bot integration into the AI Avatar monorepo. All changes are **isolated** and do not modify existing applications, routes, or infrastructure.

---

## Numbered Changelog

### 1. Created Rasa Core Configuration Files

**Location:** `apps/rasa-bot/rasa/`

- **config.yml** - Pipeline and policy configuration
  - Language: Russian (ru)
  - Tokenizer: WhitespaceTokenizer
  - Featurizers: RegexFeaturizer, LexicalSyntacticFeaturizer, CountVectorsFeaturizer
  - Classifier: DIETClassifier (25 epochs)
  - Policies: RulePolicy, MemoizationPolicy, UnexpecTEDIntentPolicy, TEDPolicy
  - Pinned version: Rasa 3.6.20

- **domain.yml** - Intents, responses, and actions
  - Intents: greet, ask_capability, refresh_cache, goodbye
  - Entities: skill
  - Responses: utter_greet, utter_goodbye, utter_default
  - Custom actions: action_answer_capability, action_refresh_cache

- **credentials.yml** - Telegram connector configuration
  - Configured for long polling (webhook_url left empty)
  - Uses environment variables: TELEGRAM_TOKEN, TELEGRAM_BOT_NAME

- **endpoints.yml** - Action server endpoint
  - Action endpoint: http://actions:5055/webhook

### 2. Created NLU Training Data

**Location:** `apps/rasa-bot/rasa/data/`

- **nlu.yml** - Russian language training examples
  - Intent: greet (8 examples)
  - Intent: ask_capability (25+ examples with skill entities)
  - Intent: refresh_cache (6 examples)
  - Intent: goodbye (6 examples)

- **rules.yml** - Conversation rules
  - Rule: Greet user
  - Rule: Say goodbye
  - Rule: Answer capability question
  - Rule: Refresh Notion cache

### 3. Created Action Server Implementation

**Location:** `apps/rasa-bot/actions/`

- **requirements.txt** - Pinned Python dependencies
  - rasa-sdk==3.6.2
  - rapidfuzz==3.9.6
  - requests==2.32.3

- **actions.py** - Custom actions with Notion integration
  - Notion API integration for skills database
  - 10-minute in-memory cache (TTL: 600 seconds)
  - Fuzzy matching using RapidFuzz (token_set_ratio, 60% threshold)
  - ActionAnswerCapability: Answers skill questions with structured responses
  - ActionRefreshCache: Manual cache refresh via /refresh command
  - Environment variables: NOTION_SECRET, NOTION_DB, CAL_LINK

### 4. Created Docker Compose Configuration

**Location:** `infra/compose/rasa-bot.compose.yaml`

- Isolated Docker Compose file (does not modify existing compose files)
- Services:
  - **rasa**: Official rasa/rasa:3.6.20 image
    - Command: run --enable-api --cors * --port 5005
    - Volumes: mounts apps/rasa-bot/rasa to /app
    - Ports: 5005:5005
    - Env file: .env.rasa-bot
    - Depends on: actions
  
  - **actions**: Official rasa/rasa-sdk:3.6.2 image
    - Volumes: mounts apps/rasa-bot/actions to /app/actions
    - Ports: 5055:5055
    - Environment: NOTION_SECRET, NOTION_DB, CAL_LINK

- Network: rasa-network (isolated bridge network)
- Restart policy: unless-stopped

### 5. Created PowerShell Development Scripts

**Location:** `scripts/`

- **rasa-bot-train.ps1** - Model training script
  - Validates Rasa folder structure
  - Runs Docker-based training with rasa/rasa:3.6.20
  - Saves model to apps/rasa-bot/rasa/models/
  - Windows-friendly with colored output

- **rasa-bot-dev.ps1** - Development startup script
  - Creates .env.rasa-bot from example if missing
  - Prompts for environment variables interactively
  - Starts Docker Compose services
  - Verifies installation with rasa --version
  - Provides usage instructions

- **rasa-bot-down.ps1** - Service shutdown script
  - Gracefully stops all Rasa bot services
  - Windows-friendly with colored output

### 6. Created Environment Configuration Template

**Location:** `apps/rasa-bot/env.rasa-bot.example`

- Template for .env.rasa-bot configuration
- Variables:
  - TELEGRAM_TOKEN (required)
  - TELEGRAM_BOT_NAME (required)
  - NOTION_SECRET (required)
  - NOTION_DB (required)
  - CAL_LINK (optional)
  - RASA_LOG_LEVEL (default: INFO)

### 7. Created Comprehensive Documentation

**Location:** `apps/rasa-bot/README.md`

- Complete setup and usage guide
- Notion database schema specification
- Quick start instructions
- PowerShell command reference
- Troubleshooting section
- Development guidelines
- Production deployment instructions
- Isolation notes

---

## Unified Diff

### File: apps/rasa-bot/rasa/config.yml (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/rasa/config.yml
@@ -0,0 +1,34 @@
+# Rasa OSS Assistant Configuration
+# Isolated bot configuration - does not affect existing AI Avatar services
+# Version: Rasa 3.6.20
+
+recipe: default.v1
+language: ru
+
+pipeline:
+  - name: WhitespaceTokenizer
+  - name: RegexFeaturizer
+  - name: LexicalSyntacticFeaturizer
+  - name: CountVectorsFeaturizer
+    analyzer: char_wb
+    min_ngram: 1
+    max_ngram: 4
+  - name: DIETClassifier
+    epochs: 25
+    constrain_similarities: true
+  - name: EntitySynonymMapper
+  - name: ResponseSelector
+    epochs: 25
+    constrain_similarities: true
+
+policies:
+  - name: MemoizationPolicy
+  - name: RulePolicy
+  - name: UnexpecTEDIntentPolicy
+    max_history: 5
+    epochs: 100
+  - name: TEDPolicy
+    max_history: 5
+    epochs: 25
+    constrain_similarities: true
+
```

### File: apps/rasa-bot/rasa/domain.yml (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/rasa/domain.yml
@@ -0,0 +1,46 @@
+# Rasa OSS Assistant Domain
+# Isolated bot domain - does not affect existing AI Avatar services
+# Version: Rasa 3.6.20
+
+version: "3.1"
+
+intents:
+  - greet
+  - ask_capability
+  - refresh_cache
+  - goodbye
+
+entities:
+  - skill
+
+slots:
+  skill:
+    type: text
+    influence_conversation: false
+    mappings:
+      - type: from_text
+        conditions:
+          - active_loop: null
+            requested_slot: null
+
+responses:
+  utter_greet:
+    - text: "Привет! Я бот-помощник. Спроси меня о навыках и опыте, например: 'умеешь ли ты kubernetes?'"
+  
+  utter_goodbye:
+    - text: "До встречи! 👋"
+  
+  utter_default:
+    - text: "Извините, я не понял. Попробуйте спросить о конкретном навыке или технологии."
+
+actions:
+  - action_answer_capability
+  - action_refresh_cache
+
+session_config:
+  session_expiration_time: 60
+  carry_over_slots_to_new_session: false
+
```

### File: apps/rasa-bot/rasa/data/nlu.yml (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/rasa/data/nlu.yml
@@ -0,0 +1,69 @@
+# Rasa OSS Assistant NLU Training Data
+# Isolated bot NLU - does not affect existing AI Avatar services
+# Russian language examples
+
+version: "3.1"
+
+nlu:
+- intent: greet
+  examples: |
+    - привет
+    - здравствуй
+    - добрый день
+    - hi
+    - hello
+    - приветствую
+    - здорова
+    - хай
+
+- intent: ask_capability
+  examples: |
+    - умеешь ли ты [kubernetes](skill)?
+    - знаешь ли [python](skill)?
+    - опыт работы с [docker](skill)
+    - владеешь [react](skill)?
+    - есть опыт с [postgresql](skill)?
+    - работал с [terraform](skill)?
+    - умеешь [golang](skill)?
+    - знаком с [aws](skill)?
+    - навыки [fastapi](skill)
+    - опыт [ci/cd](skill)
+    - [typescript](skill) знаешь?
+    - [микросервисы](skill)
+    - можешь [nginx](skill)?
+    - [rabbitmq](skill) используешь?
+    - что с [graphql](skill)?
+    - умеешь [mongodb](skill)
+    - опыт [kafka](skill)
+    - владение [ansible](skill)
+    - [redis](skill) знаешь
+    - работал с [jenkins](skill)
+    - что знаешь про [kubernetes](skill)
+    - расскажи про опыт с [docker](skill)
+    - какой уровень [python](skill)
+    - сколько лет [java](skill)
+    - примеры работы с [react](skill)
+
+- intent: refresh_cache
+  examples: |
+    - /refresh
+    - обновить кеш
+    - refresh
+    - reload
+    - перезагрузи данные
+    - обнови информацию
+    - синхронизируй с notion
+
+- intent: goodbye
+  examples: |
+    - пока
+    - до свидания
+    - bye
+    - goodbye
+    - увидимся
+    - всего доброго
+
```

### File: apps/rasa-bot/rasa/data/rules.yml (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/rasa/data/rules.yml
@@ -0,0 +1,24 @@
+# Rasa OSS Assistant Rules
+# Isolated bot rules - does not affect existing AI Avatar services
+
+version: "3.1"
+
+rules:
+- rule: Greet user
+  steps:
+  - intent: greet
+  - action: utter_greet
+
+- rule: Say goodbye
+  steps:
+  - intent: goodbye
+  - action: utter_goodbye
+
+- rule: Answer capability question
+  steps:
+  - intent: ask_capability
+  - action: action_answer_capability
+
+- rule: Refresh Notion cache
+  steps:
+  - intent: refresh_cache
+  - action: action_refresh_cache
+
```

### File: apps/rasa-bot/rasa/credentials.yml (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/rasa/credentials.yml
@@ -0,0 +1,12 @@
+# Rasa OSS Assistant Credentials
+# Isolated bot credentials - does not affect existing AI Avatar services
+# Telegram connector configured for long polling (no webhook)
+
+# Telegram connector (polling mode - leave webhook_url empty)
+telegram:
+  access_token: "${TELEGRAM_TOKEN}"
+  verify: "${TELEGRAM_BOT_NAME}"
+  webhook_url: ""  # Empty for polling mode
+
+# REST API (always enabled)
+rest:
+  # no additional config needed
+
```

### File: apps/rasa-bot/rasa/endpoints.yml (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/rasa/endpoints.yml
@@ -0,0 +1,14 @@
+# Rasa OSS Assistant Endpoints
+# Isolated bot endpoints - does not affect existing AI Avatar services
+
+action_endpoint:
+  url: "http://actions:5055/webhook"
+
+# Tracker store (in-memory for MVP)
+# tracker_store:
+#   type: InMemoryTrackerStore
+
+# Event broker (disabled for MVP)
+# event_broker:
+#   type: pika
+#   url: rabbitmq
+#   username: guest
+#   password: guest
+
```

### File: apps/rasa-bot/actions/requirements.txt (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/actions/requirements.txt
@@ -0,0 +1,6 @@
+# Rasa Action Server Dependencies
+# Isolated bot dependencies - does not affect existing AI Avatar services
+# Pinned versions for deterministic builds
+
+rasa-sdk==3.6.2
+rapidfuzz==3.9.6
+requests==2.32.3
+
```

### File: apps/rasa-bot/actions/actions.py (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/actions/actions.py
@@ -0,0 +1,255 @@
+# Rasa Action Server - Custom Actions
+# Isolated bot actions - does not affect existing AI Avatar services
+# Implements Notion-based skills lookup with fuzzy matching
+
+import os
+import time
+import logging
+from typing import Any, Text, Dict, List, Optional
+
+import requests
+from rapidfuzz import fuzz
+from rasa_sdk import Action, Tracker
+from rasa_sdk.executor import CollectingDispatcher
+from rasa_sdk.events import SlotSet
+
+logger = logging.getLogger(__name__)
+
+# In-memory cache configuration
+CACHE_TTL_SECONDS = 600  # 10 minutes
+_cache = {
+    "data": [],
+    "timestamp": 0
+}
+
+
+def fetch_notion_skills() -> List[Dict[str, Any]]:
+    """
+    Fetch skills/experience from Notion database.
+    Returns list of skill records with structure:
+    [
+        {
+            "name": "Kubernetes",
+            "level": "Advanced",
+            "years": 3,
+            "tags": ["DevOps", "Cloud"],
+            "keywords": ["k8s", "kubernetes", "кубер"],
+            "examples": "Deployed multi-region clusters..."
+        },
+        ...
+    ]
+    """
+    notion_secret = os.getenv("NOTION_SECRET", "")
+    notion_db = os.getenv("NOTION_DB", "")
+    
+    if not notion_secret or not notion_db:
+        logger.error("NOTION_SECRET or NOTION_DB not configured")
+        return []
+    
+    headers = {
+        "Authorization": f"Bearer {notion_secret}",
+        "Notion-Version": "2022-06-28",
+        "Content-Type": "application/json"
+    }
+    
+    url = f"https://api.notion.com/v1/databases/{notion_db}/query"
+    
+    try:
+        response = requests.post(url, headers=headers, json={}, timeout=10)
+        response.raise_for_status()
+        results = response.json().get("results", [])
+        
+        skills = []
+        for page in results:
+            props = page.get("properties", {})
+            
+            # Extract properties based on expected Notion schema
+            name_prop = props.get("Name", {}) or props.get("Название", {})
+            level_prop = props.get("Level", {}) or props.get("Уровень", {})
+            years_prop = props.get("Years", {}) or props.get("Лет", {})
+            tags_prop = props.get("Tags", {}) or props.get("Теги", {})
+            keywords_prop = props.get("Keywords", {}) or props.get("Ключевые слова", {})
+            examples_prop = props.get("Examples", {}) or props.get("Примеры", {})
+            
+            # Parse name
+            name = ""
+            if name_prop.get("type") == "title":
+                title_list = name_prop.get("title", [])
+                if title_list:
+                    name = title_list[0].get("plain_text", "")
+            
+            # Parse level
+            level = ""
+            if level_prop.get("type") == "select":
+                select_obj = level_prop.get("select")
+                if select_obj:
+                    level = select_obj.get("name", "")
+            elif level_prop.get("type") == "rich_text":
+                rich_text_list = level_prop.get("rich_text", [])
+                if rich_text_list:
+                    level = rich_text_list[0].get("plain_text", "")
+            
+            # Parse years
+            years = 0
+            if years_prop.get("type") == "number":
+                years = years_prop.get("number", 0) or 0
+            
+            # Parse tags
+            tags = []
+            if tags_prop.get("type") == "multi_select":
+                tags = [t.get("name", "") for t in tags_prop.get("multi_select", [])]
+            
+            # Parse keywords
+            keywords = []
+            if keywords_prop.get("type") == "rich_text":
+                rich_text_list = keywords_prop.get("rich_text", [])
+                if rich_text_list:
+                    keywords_str = rich_text_list[0].get("plain_text", "")
+                    keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
+            elif keywords_prop.get("type") == "multi_select":
+                keywords = [k.get("name", "").lower() for k in keywords_prop.get("multi_select", [])]
+            
+            # Parse examples
+            examples = ""
+            if examples_prop.get("type") == "rich_text":
+                rich_text_list = examples_prop.get("rich_text", [])
+                if rich_text_list:
+                    examples = rich_text_list[0].get("plain_text", "")
+            
+            if name:
+                skills.append({
+                    "name": name,
+                    "level": level,
+                    "years": years,
+                    "tags": tags,
+                    "keywords": keywords,
+                    "examples": examples
+                })
+        
+        logger.info(f"Fetched {len(skills)} skills from Notion")
+        return skills
+    
+    except requests.RequestException as e:
+        logger.error(f"Failed to fetch from Notion: {e}")
+        return []
+
+
+def get_cached_skills(force_refresh: bool = False) -> List[Dict[str, Any]]:
+    """
+    Get skills from cache or fetch from Notion if cache is expired.
+    """
+    global _cache
+    
+    current_time = time.time()
+    cache_age = current_time - _cache["timestamp"]
+    
+    if force_refresh or cache_age > CACHE_TTL_SECONDS or not _cache["data"]:
+        logger.info("Refreshing skills cache from Notion")
+        _cache["data"] = fetch_notion_skills()
+        _cache["timestamp"] = current_time
+    else:
+        logger.info(f"Using cached skills (age: {int(cache_age)}s)")
+    
+    return _cache["data"]
+
+
+def find_best_skill_match(query: str, skills: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
+    """
+    Find best matching skill using fuzzy matching (RapidFuzz).
+    Uses token_set_ratio for flexible matching.
+    """
+    if not query or not skills:
+        return None
+    
+    query_lower = query.lower().strip()
+    best_match = None
+    best_score = 0
+    
+    for skill in skills:
+        # Check exact keyword match first
+        if query_lower in skill["keywords"]:
+            return skill
+        
+        # Fuzzy match against name
+        name_score = fuzz.token_set_ratio(query_lower, skill["name"].lower())
+        
+        # Fuzzy match against keywords
+        keyword_scores = [fuzz.token_set_ratio(query_lower, kw) for kw in skill["keywords"]]
+        max_keyword_score = max(keyword_scores) if keyword_scores else 0
+        
+        # Take the best score
+        score = max(name_score, max_keyword_score)
+        
+        if score > best_score:
+            best_score = score
+            best_match = skill
+    
+    # Return match if score is above threshold
+    if best_score >= 60:  # 60% similarity threshold
+        logger.info(f"Found match: {best_match['name']} (score: {best_score})")
+        return best_match
+    
+    logger.info(f"No good match found for '{query}' (best score: {best_score})")
+    return None
+
+
+class ActionAnswerCapability(Action):
+    """
+    Custom action to answer capability/skill questions.
+    """
+    
+    def name(self) -> Text:
+        return "action_answer_capability"
+    
+    def run(self, dispatcher: CollectingDispatcher,
+            tracker: Tracker,
+            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
+        
+        # Extract skill from user message
+        user_message = tracker.latest_message.get("text", "")
+        logger.info(f"Processing capability query: {user_message}")
+        
+        # Get skills from cache
+        skills = get_cached_skills()
+        
+        if not skills:
+            cal_link = os.getenv("CAL_LINK", "")
+            msg = "К сожалению, не могу загрузить информацию о навыках. Попробуйте позже."
+            if cal_link:
+                msg += f"\n\nДля детального обсуждения можно забронировать встречу: {cal_link}"
+            dispatcher.utter_message(text=msg)
+            return []
+        
+        # Find best matching skill
+        match = find_best_skill_match(user_message, skills)
+        
+        if match:
+            # Format response
+            verdict = f"✅ Да, есть опыт с {match['name']}"
+            
+            details = []
+            if match["level"]:
+                details.append(f"Уровень: {match['level']}")
+            if match["years"] and match["years"] > 0:
+                years_word = "год" if match["years"] == 1 else "года" if match["years"] < 5 else "лет"
+                details.append(f"Опыт: {match['years']} {years_word}")
+            if match["tags"]:
+                details.append(f"Область: {', '.join(match['tags'])}")
+            
+            response = verdict
+            if details:
+                response += "\n" + "\n".join(details)
+            
+            if match["examples"]:
+                response += f"\n\nПримеры:\n{match['examples']}"
+            
+            # Add calendar link if available
+            cal_link = os.getenv("CAL_LINK", "")
+            if cal_link:
+                response += f"\n\nДля детального обсуждения: {cal_link}"
+            
+            dispatcher.utter_message(text=response)
+        else:
+            # No match found
+            cal_link = os.getenv("CAL_LINK", "")
+            msg = f"Не нашёл информацию по запросу '{user_message}'. Попробуйте переформулировать или спросите о другом навыке."
+            if cal_link:
+                msg += f"\n\nДля детального обсуждения: {cal_link}"
+            dispatcher.utter_message(text=msg)
+        
+        return []
+
+
+class ActionRefreshCache(Action):
+    """
+    Custom action to force refresh Notion cache.
+    """
+    
+    def name(self) -> Text:
+        return "action_refresh_cache"
+    
+    def run(self, dispatcher: CollectingDispatcher,
+            tracker: Tracker,
+            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
+        
+        logger.info("Manual cache refresh requested")
+        
+        # Force refresh cache
+        skills = get_cached_skills(force_refresh=True)
+        
+        if skills:
+            dispatcher.utter_message(
+                text=f"✅ Кеш обновлён! Загружено {len(skills)} навыков из Notion."
+            )
+        else:
+            dispatcher.utter_message(
+                text="❌ Не удалось обновить кеш. Проверьте настройки NOTION_SECRET и NOTION_DB."
+            )
+        
+        return []
+
```

### File: infra/compose/rasa-bot.compose.yaml (NEW)

```diff
--- /dev/null
+++ infra/compose/rasa-bot.compose.yaml
@@ -0,0 +1,46 @@
+# Docker Compose for Rasa OSS Assistant
+# Isolated bot infrastructure - does not affect existing AI Avatar services
+# Use: docker compose -f infra/compose/rasa-bot.compose.yaml up -d
+
+version: '3.8'
+
+services:
+  rasa:
+    image: rasa/rasa:3.6.20
+    container_name: rasa-bot
+    command:
+      - run
+      - --enable-api
+      - --cors
+      - "*"
+      - --port
+      - "5005"
+    volumes:
+      - ../../apps/rasa-bot/rasa:/app
+    ports:
+      - "5005:5005"
+    env_file:
+      - ../../.env.rasa-bot
+    environment:
+      - RASA_LOG_LEVEL=${RASA_LOG_LEVEL:-INFO}
+    depends_on:
+      - actions
+    networks:
+      - rasa-network
+    restart: unless-stopped
+
+  actions:
+    image: rasa/rasa-sdk:3.6.2
+    container_name: rasa-actions
+    volumes:
+      - ../../apps/rasa-bot/actions:/app/actions
+    ports:
+      - "5055:5055"
+    environment:
+      - NOTION_SECRET=${NOTION_SECRET}
+      - NOTION_DB=${NOTION_DB}
+      - CAL_LINK=${CAL_LINK}
+    networks:
+      - rasa-network
+    restart: unless-stopped
+
+networks:
+  rasa-network:
+    driver: bridge
+
```

### File: scripts/rasa-bot-train.ps1 (NEW)

```diff
--- /dev/null
+++ scripts/rasa-bot-train.ps1
@@ -0,0 +1,52 @@
+# Rasa Bot Training Script for Windows/PowerShell
+# Trains the Rasa model using Docker
+# Usage: .\scripts\rasa-bot-train.ps1
+
+$ErrorActionPreference = "Stop"
+
+Write-Host "==================================" -ForegroundColor Cyan
+Write-Host "Rasa Bot Training Script" -ForegroundColor Cyan
+Write-Host "==================================" -ForegroundColor Cyan
+Write-Host ""
+
+# Check if rasa folder exists
+$rasaPath = "apps\rasa-bot\rasa"
+if (-Not (Test-Path $rasaPath)) {
+    Write-Host "ERROR: Rasa folder not found at $rasaPath" -ForegroundColor Red
+    exit 1
+}
+
+Write-Host "✓ Found Rasa folder at $rasaPath" -ForegroundColor Green
+
+# Get absolute path for volume mount
+$absoluteRasaPath = (Resolve-Path $rasaPath).Path
+
+Write-Host ""
+Write-Host "Starting training..." -ForegroundColor Yellow
+Write-Host "This may take several minutes depending on your machine." -ForegroundColor Yellow
+Write-Host ""
+
+# Run training
+try {
+    docker run --rm -v "${absoluteRasaPath}:/app" rasa/rasa:3.6.20 train --fixed-model-name rasa-bot-model
+    
+    if ($LASTEXITCODE -eq 0) {
+        Write-Host ""
+        Write-Host "==================================" -ForegroundColor Green
+        Write-Host "✓ Training completed successfully!" -ForegroundColor Green
+        Write-Host "==================================" -ForegroundColor Green
+        Write-Host ""
+        Write-Host "Model saved to: $rasaPath\models" -ForegroundColor Cyan
+        
+        # List models
+        if (Test-Path "$rasaPath\models") {
+            Write-Host ""
+            Write-Host "Available models:" -ForegroundColor Cyan
+            Get-ChildItem "$rasaPath\models" | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor White }
+        }
+    } else {
+        Write-Host ""
+        Write-Host "ERROR: Training failed with exit code $LASTEXITCODE" -ForegroundColor Red
+        exit 1
+    }
+} catch {
+    Write-Host ""
+    Write-Host "ERROR: Training failed with exception:" -ForegroundColor Red
+    Write-Host $_.Exception.Message -ForegroundColor Red
+    exit 1
+}
+
+Write-Host ""
+Write-Host "Next steps:" -ForegroundColor Cyan
+Write-Host "  1. Run .\scripts\rasa-bot-dev.ps1 to start the bot" -ForegroundColor White
+Write-Host "  2. Test the bot in Telegram" -ForegroundColor White
+Write-Host ""
+
```

### File: scripts/rasa-bot-dev.ps1 (NEW)

```diff
--- /dev/null
+++ scripts/rasa-bot-dev.ps1
@@ -0,0 +1,102 @@
+# Rasa Bot Development Startup Script for Windows/PowerShell
+# Starts Rasa bot services using Docker Compose
+# Usage: .\scripts\rasa-bot-dev.ps1
+
+$ErrorActionPreference = "Stop"
+
+Write-Host "==================================" -ForegroundColor Cyan
+Write-Host "Rasa Bot Development Startup" -ForegroundColor Cyan
+Write-Host "==================================" -ForegroundColor Cyan
+Write-Host ""
+
+# Check if .env.rasa-bot exists, if not copy from example
+$envFile = ".env.rasa-bot"
+$envExample = ".env.rasa-bot.example"
+
+if (-Not (Test-Path $envFile)) {
+    Write-Host "⚠ Environment file not found. Creating from example..." -ForegroundColor Yellow
+    
+    if (Test-Path $envExample) {
+        Copy-Item $envExample $envFile
+        Write-Host "✓ Created $envFile from $envExample" -ForegroundColor Green
+        Write-Host ""
+        Write-Host "IMPORTANT: Please fill in the following values in $envFile" -ForegroundColor Yellow
+        Write-Host ""
+        
+        # Prompt for required values
+        $telegramToken = Read-Host "Enter TELEGRAM_TOKEN (from @BotFather)"
+        $telegramBotName = Read-Host "Enter TELEGRAM_BOT_NAME (bot username without @)"
+        $notionSecret = Read-Host "Enter NOTION_SECRET (Notion integration secret)"
+        $notionDb = Read-Host "Enter NOTION_DB (Notion database ID)"
+        $calLink = Read-Host "Enter CAL_LINK (optional calendar link, press Enter to skip)"
+        
+        # Update .env file
+        $envContent = Get-Content $envFile
+        $envContent = $envContent -replace "TELEGRAM_TOKEN=", "TELEGRAM_TOKEN=$telegramToken"
+        $envContent = $envContent -replace "TELEGRAM_BOT_NAME=", "TELEGRAM_BOT_NAME=$telegramBotName"
+        $envContent = $envContent -replace "NOTION_SECRET=", "NOTION_SECRET=$notionSecret"
+        $envContent = $envContent -replace "NOTION_DB=", "NOTION_DB=$notionDb"
+        if ($calLink) {
+            $envContent = $envContent -replace "CAL_LINK=", "CAL_LINK=$calLink"
+        }
+        $envContent | Set-Content $envFile
+        
+        Write-Host ""
+        Write-Host "✓ Environment file configured" -ForegroundColor Green
+    } else {
+        Write-Host "ERROR: Example file $envExample not found" -ForegroundColor Red
+        exit 1
+    }
+} else {
+    Write-Host "✓ Found environment file: $envFile" -ForegroundColor Green
+}
+
+# Check if model exists
+$modelPath = "apps\rasa-bot\rasa\models"
+if (-Not (Test-Path $modelPath) -or (Get-ChildItem $modelPath -Filter *.tar.gz -ErrorAction SilentlyContinue).Count -eq 0) {
+    Write-Host ""
+    Write-Host "⚠ No trained model found!" -ForegroundColor Yellow
+    Write-Host "You need to train the model first using:" -ForegroundColor Yellow
+    Write-Host "  .\scripts\rasa-bot-train.ps1" -ForegroundColor White
+    Write-Host ""
+    $response = Read-Host "Continue without trained model? (y/N)"
+    if ($response -ne "y" -and $response -ne "Y") {
+        Write-Host "Exiting. Please train the model first." -ForegroundColor Yellow
+        exit 0
+    }
+}
+
+Write-Host ""
+Write-Host "Starting Rasa bot services..." -ForegroundColor Yellow
+
+# Start services
+try {
+    docker compose -f infra/compose/rasa-bot.compose.yaml up -d
+    
+    if ($LASTEXITCODE -eq 0) {
+        Write-Host ""
+        Write-Host "✓ Services started successfully!" -ForegroundColor Green
+        Write-Host ""
+        
+        # Wait for services to be ready
+        Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
+        Start-Sleep -Seconds 5
+        
+        # Check Rasa version
+        Write-Host ""
+        Write-Host "Verifying Rasa installation:" -ForegroundColor Cyan
+        docker exec rasa-bot rasa --version
+        
+        Write-Host ""
+        Write-Host "==================================" -ForegroundColor Green
+        Write-Host "✓ Rasa Bot is running!" -ForegroundColor Green
+        Write-Host "==================================" -ForegroundColor Green
+        Write-Host ""
+        Write-Host "Services:" -ForegroundColor Cyan
+        Write-Host "  - Rasa API:        http://localhost:5005" -ForegroundColor White
+        Write-Host "  - Action Server:   http://localhost:5055" -ForegroundColor White
+        Write-Host ""
+        Write-Host "To enable Telegram polling:" -ForegroundColor Cyan
+        Write-Host "  docker exec -it rasa-bot rasa run --connector telegram --port 5005" -ForegroundColor White
+        Write-Host ""
+        Write-Host "Useful commands:" -ForegroundColor Cyan
+        Write-Host "  View logs:       docker compose -f infra/compose/rasa-bot.compose.yaml logs -f" -ForegroundColor White
+        Write-Host "  Stop services:   .\scripts\rasa-bot-down.ps1" -ForegroundColor White
+        Write-Host "  Shell access:    docker exec -it rasa-bot bash" -ForegroundColor White
+        Write-Host ""
+    } else {
+        Write-Host ""
+        Write-Host "ERROR: Failed to start services (exit code: $LASTEXITCODE)" -ForegroundColor Red
+        exit 1
+    }
+} catch {
+    Write-Host ""
+    Write-Host "ERROR: Failed to start services:" -ForegroundColor Red
+    Write-Host $_.Exception.Message -ForegroundColor Red
+    exit 1
+}
+
```

### File: scripts/rasa-bot-down.ps1 (NEW)

```diff
--- /dev/null
+++ scripts/rasa-bot-down.ps1
@@ -0,0 +1,26 @@
+# Rasa Bot Shutdown Script for Windows/PowerShell
+# Stops Rasa bot services
+# Usage: .\scripts\rasa-bot-down.ps1
+
+$ErrorActionPreference = "Stop"
+
+Write-Host "==================================" -ForegroundColor Cyan
+Write-Host "Rasa Bot Shutdown" -ForegroundColor Cyan
+Write-Host "==================================" -ForegroundColor Cyan
+Write-Host ""
+
+Write-Host "Stopping Rasa bot services..." -ForegroundColor Yellow
+
+try {
+    docker compose -f infra/compose/rasa-bot.compose.yaml down
+    
+    if ($LASTEXITCODE -eq 0) {
+        Write-Host ""
+        Write-Host "✓ Services stopped successfully!" -ForegroundColor Green
+        Write-Host ""
+    } else {
+        Write-Host ""
+        Write-Host "ERROR: Failed to stop services (exit code: $LASTEXITCODE)" -ForegroundColor Red
+        exit 1
+    }
+} catch {
+    Write-Host ""
+    Write-Host "ERROR: Failed to stop services:" -ForegroundColor Red
+    Write-Host $_.Exception.Message -ForegroundColor Red
+    exit 1
+}
+
```

### File: apps/rasa-bot/env.rasa-bot.example (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/env.rasa-bot.example
@@ -0,0 +1,15 @@
+# Rasa OSS Assistant Environment Variables
+# Copy this file to .env.rasa-bot in the root directory and fill in your actual values
+
+# Telegram Bot Configuration
+TELEGRAM_TOKEN=
+TELEGRAM_BOT_NAME=
+
+# Notion Integration
+NOTION_SECRET=
+NOTION_DB=
+
+# Calendar/Meeting Link (optional)
+CAL_LINK=
+
+# Logging
+RASA_LOG_LEVEL=INFO
+
```

### File: apps/rasa-bot/README.md (NEW)

```diff
--- /dev/null
+++ apps/rasa-bot/README.md
@@ -0,0 +1,392 @@
+(See full README.md content - 392 lines of comprehensive documentation)
```

---

## Verification Checklist

- [x] All new files created in isolated directories (`apps/rasa-bot/`, `infra/compose/rasa-bot.compose.yaml`, `scripts/rasa-bot-*.ps1`)
- [x] No existing files modified
- [x] No changes to existing apps (api, telegram, website)
- [x] No changes to existing routes or base paths
- [x] No CI/CD modifications
- [x] Pinned versions used throughout (Rasa 3.6.20, SDK 3.6.2, RapidFuzz 3.9.6, requests 2.32.3)
- [x] Windows/PowerShell-friendly scripts
- [x] Docker-based development workflow
- [x] Telegram polling (no webhooks)
- [x] Notion integration with caching
- [x] Fuzzy matching with RapidFuzz
- [x] Comprehensive documentation

---

## File Summary

### New Files Created: 13

1. `apps/rasa-bot/rasa/config.yml` (34 lines)
2. `apps/rasa-bot/rasa/domain.yml` (46 lines)
3. `apps/rasa-bot/rasa/data/nlu.yml` (69 lines)
4. `apps/rasa-bot/rasa/data/rules.yml` (24 lines)
5. `apps/rasa-bot/rasa/credentials.yml` (12 lines)
6. `apps/rasa-bot/rasa/endpoints.yml` (14 lines)
7. `apps/rasa-bot/actions/requirements.txt` (6 lines)
8. `apps/rasa-bot/actions/actions.py` (255 lines)
9. `infra/compose/rasa-bot.compose.yaml` (46 lines)
10. `scripts/rasa-bot-train.ps1` (52 lines)
11. `scripts/rasa-bot-dev.ps1` (102 lines)
12. `scripts/rasa-bot-down.ps1` (26 lines)
13. `apps/rasa-bot/env.rasa-bot.example` (15 lines)
14. `apps/rasa-bot/README.md` (392 lines)

### Total Lines Added: 1,093 lines

### Files Modified: 0

---

## Quick Start Commands

```powershell
# 1. Train the model
.\scripts\rasa-bot-train.ps1

# 2. Start services
.\scripts\rasa-bot-dev.ps1

# 3. Enable Telegram polling
docker exec -it rasa-bot rasa run --connector telegram --port 5005

# 4. Stop services
.\scripts\rasa-bot-down.ps1
```

---

## Environment Setup

Before running, you need to:

1. **Create Notion Integration** at https://www.notion.so/my-integrations
2. **Create Notion Database** with the required schema (see README)
3. **Create Telegram Bot** via @BotFather
4. **Copy environment file**:
   ```powershell
   Copy-Item apps/rasa-bot/env.rasa-bot.example .env.rasa-bot
   ```
5. **Fill in credentials** in `.env.rasa-bot`

---

## Isolation Guarantees

✅ **No impact on existing services:**
- Separate folder structure (`apps/rasa-bot/`)
- Separate Docker Compose file
- Separate network (`rasa-network`)
- Separate ports (5005, 5055)
- Separate environment file

✅ **Safe to remove:**
Delete `apps/rasa-bot/`, `infra/compose/rasa-bot.compose.yaml`, `scripts/rasa-bot-*.ps1`, and `.env.rasa-bot` to completely remove the integration.

---

**End of Change Summary**

