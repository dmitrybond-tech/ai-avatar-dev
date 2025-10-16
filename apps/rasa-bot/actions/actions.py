# Rasa Action Server - Custom Actions
# Isolated bot actions - does not affect existing AI Avatar services
# Implements Notion-based skills lookup with fuzzy matching

import os
import time
import logging
from typing import Any, Text, Dict, List, Optional

import requests
from rapidfuzz import fuzz
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

logger = logging.getLogger(__name__)

# In-memory cache configuration
CACHE_TTL_SECONDS = 600  # 10 minutes
_cache = {
    "data": [],
    "timestamp": 0
}


def fetch_notion_skills() -> List[Dict[str, Any]]:
    """
    Fetch skills/experience from Notion database.
    Returns list of skill records with structure:
    [
        {
            "name": "Kubernetes",
            "level": "Advanced",
            "years": 3,
            "tags": ["DevOps", "Cloud"],
            "keywords": ["k8s", "kubernetes", "кубер"],
            "examples": "Deployed multi-region clusters..."
        },
        ...
    ]
    """
    notion_secret = os.getenv("NOTION_SECRET", "")
    notion_db = os.getenv("NOTION_DB", "")
    
    if not notion_secret or not notion_db:
        logger.error("NOTION_SECRET or NOTION_DB not configured")
        return []
    
    headers = {
        "Authorization": f"Bearer {notion_secret}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.notion.com/v1/databases/{notion_db}/query"
    
    try:
        response = requests.post(url, headers=headers, json={}, timeout=10)
        response.raise_for_status()
        results = response.json().get("results", [])
        
        skills = []
        for page in results:
            props = page.get("properties", {})
            
            # Extract properties based on expected Notion schema
            name_prop = props.get("Name", {}) or props.get("Название", {})
            level_prop = props.get("Level", {}) or props.get("Уровень", {})
            years_prop = props.get("Years", {}) or props.get("Лет", {})
            tags_prop = props.get("Tags", {}) or props.get("Теги", {})
            keywords_prop = props.get("Keywords", {}) or props.get("Ключевые слова", {})
            examples_prop = props.get("Examples", {}) or props.get("Примеры", {})
            
            # Parse name
            name = ""
            if name_prop.get("type") == "title":
                title_list = name_prop.get("title", [])
                if title_list:
                    name = title_list[0].get("plain_text", "")
            
            # Parse level
            level = ""
            if level_prop.get("type") == "select":
                select_obj = level_prop.get("select")
                if select_obj:
                    level = select_obj.get("name", "")
            elif level_prop.get("type") == "rich_text":
                rich_text_list = level_prop.get("rich_text", [])
                if rich_text_list:
                    level = rich_text_list[0].get("plain_text", "")
            
            # Parse years
            years = 0
            if years_prop.get("type") == "number":
                years = years_prop.get("number", 0) or 0
            
            # Parse tags
            tags = []
            if tags_prop.get("type") == "multi_select":
                tags = [t.get("name", "") for t in tags_prop.get("multi_select", [])]
            
            # Parse keywords
            keywords = []
            if keywords_prop.get("type") == "rich_text":
                rich_text_list = keywords_prop.get("rich_text", [])
                if rich_text_list:
                    keywords_str = rich_text_list[0].get("plain_text", "")
                    keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
            elif keywords_prop.get("type") == "multi_select":
                keywords = [k.get("name", "").lower() for k in keywords_prop.get("multi_select", [])]
            
            # Parse examples
            examples = ""
            if examples_prop.get("type") == "rich_text":
                rich_text_list = examples_prop.get("rich_text", [])
                if rich_text_list:
                    examples = rich_text_list[0].get("plain_text", "")
            
            if name:
                skills.append({
                    "name": name,
                    "level": level,
                    "years": years,
                    "tags": tags,
                    "keywords": keywords,
                    "examples": examples
                })
        
        logger.info(f"Fetched {len(skills)} skills from Notion")
        return skills
    
    except requests.RequestException as e:
        logger.error(f"Failed to fetch from Notion: {e}")
        return []


def get_cached_skills(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Get skills from cache or fetch from Notion if cache is expired.
    """
    global _cache
    
    current_time = time.time()
    cache_age = current_time - _cache["timestamp"]
    
    if force_refresh or cache_age > CACHE_TTL_SECONDS or not _cache["data"]:
        logger.info("Refreshing skills cache from Notion")
        _cache["data"] = fetch_notion_skills()
        _cache["timestamp"] = current_time
    else:
        logger.info(f"Using cached skills (age: {int(cache_age)}s)")
    
    return _cache["data"]


def find_best_skill_match(query: str, skills: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Find best matching skill using fuzzy matching (RapidFuzz).
    Uses token_set_ratio for flexible matching.
    """
    if not query or not skills:
        return None
    
    query_lower = query.lower().strip()
    best_match = None
    best_score = 0
    
    for skill in skills:
        # Check exact keyword match first
        if query_lower in skill["keywords"]:
            return skill
        
        # Fuzzy match against name
        name_score = fuzz.token_set_ratio(query_lower, skill["name"].lower())
        
        # Fuzzy match against keywords
        keyword_scores = [fuzz.token_set_ratio(query_lower, kw) for kw in skill["keywords"]]
        max_keyword_score = max(keyword_scores) if keyword_scores else 0
        
        # Take the best score
        score = max(name_score, max_keyword_score)
        
        if score > best_score:
            best_score = score
            best_match = skill
    
    # Return match if score is above threshold
    if best_score >= 60:  # 60% similarity threshold
        logger.info(f"Found match: {best_match['name']} (score: {best_score})")
        return best_match
    
    logger.info(f"No good match found for '{query}' (best score: {best_score})")
    return None


class ActionAnswerCapability(Action):
    """
    Custom action to answer capability/skill questions.
    """
    
    def name(self) -> Text:
        return "action_answer_capability"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Extract skill from user message
        user_message = tracker.latest_message.get("text", "")
        logger.info(f"Processing capability query: {user_message}")
        
        # Get skills from cache
        skills = get_cached_skills()
        
        if not skills:
            cal_link = os.getenv("CAL_LINK", "")
            msg = "К сожалению, не могу загрузить информацию о навыках. Попробуйте позже."
            if cal_link:
                msg += f"\n\nДля детального обсуждения можно забронировать встречу: {cal_link}"
            dispatcher.utter_message(text=msg)
            return []
        
        # Find best matching skill
        match = find_best_skill_match(user_message, skills)
        
        if match:
            # Format response
            verdict = f"✅ Да, есть опыт с {match['name']}"
            
            details = []
            if match["level"]:
                details.append(f"Уровень: {match['level']}")
            if match["years"] and match["years"] > 0:
                years_word = "год" if match["years"] == 1 else "года" if match["years"] < 5 else "лет"
                details.append(f"Опыт: {match['years']} {years_word}")
            if match["tags"]:
                details.append(f"Область: {', '.join(match['tags'])}")
            
            response = verdict
            if details:
                response += "\n" + "\n".join(details)
            
            if match["examples"]:
                response += f"\n\nПримеры:\n{match['examples']}"
            
            # Add calendar link if available
            cal_link = os.getenv("CAL_LINK", "")
            if cal_link:
                response += f"\n\nДля детального обсуждения: {cal_link}"
            
            dispatcher.utter_message(text=response)
        else:
            # No match found
            cal_link = os.getenv("CAL_LINK", "")
            msg = f"Не нашёл информацию по запросу '{user_message}'. Попробуйте переформулировать или спросите о другом навыке."
            if cal_link:
                msg += f"\n\nДля детального обсуждения: {cal_link}"
            dispatcher.utter_message(text=msg)
        
        return []


class ActionRefreshCache(Action):
    """
    Custom action to force refresh Notion cache.
    """
    
    def name(self) -> Text:
        return "action_refresh_cache"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        logger.info("Manual cache refresh requested")
        
        # Force refresh cache
        skills = get_cached_skills(force_refresh=True)
        
        if skills:
            dispatcher.utter_message(
                text=f"✅ Кеш обновлён! Загружено {len(skills)} навыков из Notion."
            )
        else:
            dispatcher.utter_message(
                text="❌ Не удалось обновить кеш. Проверьте настройки NOTION_SECRET и NOTION_DB."
            )
        
        return []

