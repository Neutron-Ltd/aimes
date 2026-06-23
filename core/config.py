"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """NEUTRON MES AI Assistant — Phase 1 settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "NEUTRON MES AI Assistant"
    app_version: str = "0.1.0"
    debug: bool = False

    # Mock database bridge (F0.4) — replace with real DSN in production
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "mes_db"
    db_user: str = "mes_readonly"
    db_pool_size: int = 5

    # Default workshop when no RBAC header is supplied (dev only)
    default_workshop_id: str = "WS-001"


@lru_cache
def get_settings() -> Settings:
    return Settings()
