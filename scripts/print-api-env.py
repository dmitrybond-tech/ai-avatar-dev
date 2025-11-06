#!/usr/bin/env python3
import os


def mask(value: str) -> str:
    if value is None:
        return "<none>"
    v = str(value)
    if not v:
        return "<empty>"
    return f"len={len(v)} first=*** last=***"


def main() -> None:
    print("API env (masked):")
    print(f"NOTION_API_KEY: {mask(os.getenv('NOTION_API_KEY'))}")
    print(f"NOTION_SECRET:  {mask(os.getenv('NOTION_SECRET'))}")
    print(f"NOTION_PUBLIC_TASKS_DB_ID: {mask(os.getenv('NOTION_PUBLIC_TASKS_DB_ID'))}")
    print(f"NOTION_DB: {mask(os.getenv('NOTION_DB'))}")


if __name__ == "__main__":
    main()

import os


def mask(value: str, keep: int = 4) -> str:
    if not value:
        return "<EMPTY>"
    if len(value) <= keep:
        return "*" * len(value)
    return f"{'*' * (len(value) - keep)}{value[-keep:]}"


def main() -> None:
    api_key = os.getenv("NOTION_API_KEY", "")
    db_id = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "")
    timeout = os.getenv("NOTION_TIMEOUT", "")

    print(f"NOTION_API_KEY: len={len(api_key)} masked={mask(api_key)}")
    print(f"NOTION_PUBLIC_TASKS_DB_ID: len={len(db_id)} masked={mask(db_id)}")
    print(f"NOTION_TIMEOUT: {timeout or '<UNSET>'}")


if __name__ == "__main__":
    main()


