from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # Keitaro Settings (loaded from .env)
    KEITARO_API_URL: str = "https://*******************/admin_api/v1"
    KEITARO_API_KEY: str = ""
    KEITARO_DEFAULT_DOMAIN_ID: int = 1813
    KEITARO_DEFAULT_GROUP_ID: int = 10332
    KEITARO_DEFAULT_TRAFFIC_SOURCE_ID: int = 836

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./adrobot.db"
    APP_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
