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


