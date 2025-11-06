import os


def notion_token() -> str | None:
    return os.getenv("NOTION_API_KEY") or os.getenv("NOTION_SECRET")


def skills_db() -> str | None:
    return os.getenv("NOTION_DB_SKILLS") or os.getenv("NOTION_DB")


def tasks_db() -> str | None:
    return os.getenv("NOTION_PUBLIC_TASKS_DB_ID")


def notion_timeout() -> int:
    v = os.getenv("NOTION_TIMEOUT")
    try:
        return int(v) if v else 10
    except Exception:
        return 10


