"""Application settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    website_origin: str = "http://localhost:3000"
    log_level: str = "INFO"

    # Database
    postgres_user: str = "avatar"
    postgres_password: str = "avatar"
    postgres_db: str = "avatar"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_ttl_seconds: int = 3600

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""

    # LLM
    llm_provider: str = "stub"
    llm_api_key: str = ""

    # TTS
    tts_provider: str = "stub"
    tts_api_key: str = ""
    tts_voice_preset: str = "male_russian_1"

    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()

