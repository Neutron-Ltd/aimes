"""Application configuration loaded from environment variables."""

from functools import lru_cache

from datetime import date
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """NEUTRON MES AI Assistant — v0.3 settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "MES AI Assistant"
    app_version: str = "0.3.0"
    debug: bool = False

    database_url: str = Field(
        default=(
            "postgresql+asyncpg://mes_readonly:YOUR_PASSWORD@"
            "your-db-host:5432/mes_db"
        ),
        validation_alias="DATABASE_URL",
    )
    db_pool_size: int = 3
    default_workshop_id: str = "WS-001"
    default_wh_code: Optional[str] = Field(
        default=None, validation_alias="DEFAULT_WH_CODE"
    )
    dashboard_reference_date: date = Field(
        default=date(2026, 6, 21),
        validation_alias="DASHBOARD_REFERENCE_DATE",
        description="Latest MES snapshot date for dashboard lookback windows",
    )

    dashscope_api_key: str = Field(default="", validation_alias="DASHSCOPE_API_KEY")
    bailian_app_id: str = Field(default="", validation_alias="BAILIAN_APP_ID")

    rag_backend: str = Field(default="chroma", validation_alias="RAG_BACKEND")
    rag_embedding_model: str = Field(
        default="text-embedding-v2", validation_alias="RAG_EMBEDDING_MODEL"
    )
    chroma_persist_dir: str = Field(
        default="./data/chroma", validation_alias="CHROMA_PERSIST_DIR"
    )

    voice_mock: bool = Field(default=True, validation_alias="VOICE_MOCK")

    chat_db_path: str = Field(
        default="./data/chat_history.db",
        validation_alias="CHAT_DB_PATH",
        description="SQLite file for per-workshop chat history (writable, separate from MES PostgreSQL)",
    )

    dashboard_cache_enabled: bool = Field(
        default=True,
        validation_alias="DASHBOARD_CACHE_ENABLED",
    )
    dashboard_cache_db_path: str = Field(
        default="./data/dashboard_cache.db",
        validation_alias="DASHBOARD_CACHE_DB_PATH",
    )
    dashboard_cache_ttl_seconds: int = Field(
        default=900,
        validation_alias="DASHBOARD_CACHE_TTL_SECONDS",
        description="Fresh window for cached dashboard snapshots (default 15 min)",
    )
    dashboard_cache_stale_ok: bool = Field(
        default=True,
        validation_alias="DASHBOARD_CACHE_STALE_OK",
        description="Serve stale snapshots while revalidating in background",
    )
    dashboard_cache_refresh_interval_seconds: int = Field(
        default=3600,
        validation_alias="DASHBOARD_CACHE_REFRESH_INTERVAL_SECONDS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
