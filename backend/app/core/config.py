from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    environment: str = "development"
    frontend_url: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_URL")
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    migration_database_url: str | None = Field(
        default=None, validation_alias="MIGRATION_DATABASE_URL"
    )
    supabase_url: str | None = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, validation_alias="SUPABASE_ANON_KEY")
    supabase_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias="SUPABASE_SECRET_KEY",
        exclude=True,
    )
    supabase_storage_bucket: str = Field(
        default="knowledge-documents",
        validation_alias="SUPABASE_STORAGE_BUCKET",
    )
    max_document_size_bytes: int = Field(
        default=5_242_880,
        validation_alias="MAX_DOCUMENT_SIZE_BYTES",
    )
    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="GEMINI_API_KEY",
        exclude=True,
    )
    embedding_model: str = Field(
        default="gemini-embedding-001",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(default=768, gt=0, validation_alias="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=16, gt=0, validation_alias="EMBEDDING_BATCH_SIZE")
    embedding_api_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias="EMBEDDING_API_TIMEOUT_SECONDS",
    )
    embedding_max_retries: int = Field(default=2, ge=0, le=5, validation_alias="EMBEDDING_MAX_RETRIES")
    embedding_retry_backoff_seconds: float = Field(
        default=0.5,
        ge=0,
        validation_alias="EMBEDDING_RETRY_BACKOFF_SECONDS",
    )
    embedding_retry_max_backoff_seconds: float = Field(
        default=4.0,
        ge=0,
        validation_alias="EMBEDDING_RETRY_MAX_BACKOFF_SECONDS",
    )
    seed_demo_user_id: str | None = Field(default=None, validation_alias="SEED_DEMO_USER_ID")

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def frontend_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
