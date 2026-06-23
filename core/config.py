"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """NEUTRON MES AI Assistant — Phase 2 settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "NEUTRON MES AI Assistant"
    app_version: str = "0.2.0"
    debug: bool = False

    # Async PostgreSQL DSN — override via DATABASE_URL in .env for production
    database_url: str = Field(
        default=(
            "postgresql+asyncpg://mes_readonly:YOUR_PASSWORD@"
            "your-db-host:5432/mes_db"
        ),
        validation_alias="DATABASE_URL",
    )
    db_pool_size: int = 5

    # Default workshop when no RBAC header is supplied (dev only)
    default_workshop_id: str = "WS-001"

    # Alibaba Cloud Bailian (DashScope) — Intent Router (Feature 1.2)
    dashscope_api_key: str = Field(default="", validation_alias="DASHSCOPE_API_KEY")
    bailian_app_id: str = Field(default="", validation_alias="BAILIAN_APP_ID")


@lru_cache
def get_settings() -> Settings:
    return Settings()
