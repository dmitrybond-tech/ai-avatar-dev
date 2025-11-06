#!/usr/bin/env python3
"""Print masked lengths of NOTION environment variables for debugging."""
import os


def mask(value: str, keep: int = 4) -> str:
    """Mask a value, showing only the last 'keep' characters."""
    if not value:
        return "<EMPTY>"
    if len(value) <= keep:
        return "*" * len(value)
    return f"{'*' * (len(value) - keep)}{value[-keep:]}"


def main() -> None:
    """Print masked NOTION environment variables."""
    api_key = os.getenv("NOTION_API_KEY", "")
    secret = os.getenv("NOTION_SECRET", "")
    db_id = os.getenv("NOTION_PUBLIC_TASKS_DB_ID", "")
    db_legacy = os.getenv("NOTION_DB", "")
    timeout = os.getenv("NOTION_TIMEOUT", "")

    print("NOTION env vars (masked):")
    print(f"  NOTION_API_KEY: len={len(api_key)} masked={mask(api_key)}")
    print(f"  NOTION_SECRET (legacy): len={len(secret)} masked={mask(secret)}")
    print(f"  NOTION_PUBLIC_TASKS_DB_ID: len={len(db_id)} masked={mask(db_id)}")
    print(f"  NOTION_DB (legacy): len={len(db_legacy)} masked={mask(db_legacy)}")
    print(f"  NOTION_TIMEOUT: {timeout or '<UNSET>'}")


if __name__ == "__main__":
    main()
