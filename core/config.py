"""Application configuration loaded from environment variables."""

from functools import lru_cache

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
    db_pool_size: int = 5
    default_workshop_id: str = "WS-001"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
