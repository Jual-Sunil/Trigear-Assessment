"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = Field(default="AI Email Intelligence Platform")
    app_version: str = Field(default="1.0.0")
    environment: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    secret_key: str = Field(..., min_length=32)

    # -------------------------------------------------------------------------
    # API
    # -------------------------------------------------------------------------
    api_v1_prefix: str = Field(default="/api/v1")
    allowed_origins: list[str] = Field(default=["http://localhost:5173"])
    request_max_size_bytes: int = Field(default=10 * 1024 * 1024)  # 10 MB
    frontend_url: str = Field(default="http://localhost:5173")

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: PostgresDsn = Field(...)
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)
    database_pool_timeout: int = Field(default=30)
    database_echo: bool = Field(default=False)

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_url: RedisDsn = Field(...)
    redis_max_connections: int = Field(default=20)

    # -------------------------------------------------------------------------
    # Celery
    # -------------------------------------------------------------------------
    celery_broker_url: str = Field(...)
    celery_result_backend: str = Field(...)
    celery_task_serializer: str = Field(default="json")
    celery_result_serializer: str = Field(default="json")
    celery_accept_content: list[str] = Field(default=["json"])
    celery_task_max_retries: int = Field(default=3)
    celery_task_retry_backoff: int = Field(default=60)

    # -------------------------------------------------------------------------
    # Google OAuth
    # -------------------------------------------------------------------------
    google_client_id: str = Field(...)
    google_client_secret: str = Field(...)
    google_redirect_uri: str = Field(...)
    google_oauth_scopes: list[str] = Field(
        default=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/gmail.readonly",
        ]
    )

    # -------------------------------------------------------------------------
    # Token Encryption
    # -------------------------------------------------------------------------
    token_encryption_key: str = Field(..., min_length=32)

    # -------------------------------------------------------------------------
    # Gmail Sync
    # -------------------------------------------------------------------------
    gmail_sync_max_results: int = Field(default=500)
    gmail_sync_batch_size: int = Field(default=50)

    # -------------------------------------------------------------------------
    # Email Processing Concurrency
    # -------------------------------------------------------------------------
    email_processing_concurrency: int = Field(
        default=8,
        ge=1,
        le=50,
        description=(
            "Maximum number of emails whose AI pipeline runs concurrently during "
            "a sync. Bounds simultaneous LLM/API requests via an asyncio.Semaphore."
        ),
    )
    gmail_fetch_concurrency: int = Field(
        default=10,
        ge=1,
        le=50,
        description=(
            "Maximum number of Gmail message bodies fetched concurrently during a "
            "sync."
        ),
    )
    classification_batch_enabled: bool = Field(
        default=True,
        description=(
            "When True, classify all newly synced emails in a single batched "
            "zero-shot inference call instead of one call per email."
        ),
    )

    # -------------------------------------------------------------------------
    # AI / HuggingFace
    # -------------------------------------------------------------------------
    huggingface_cache_dir: str = Field(default="/tmp/hf_cache")
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2"
    )
    classification_model_name: str = Field(default="facebook/bart-large-mnli")
    classification_confidence_threshold: float = Field(default=0.35)
    embedding_dimension: int = Field(default=384)

    # -------------------------------------------------------------------------
    # LLM Providers
    # -------------------------------------------------------------------------
    llm_provider: Literal["openai", "claude", "gemini", "openrouter", "huggingface"] = Field(default="huggingface")
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o")
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-opus-4-5")
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-1.5-pro")
    openrouter_api_key: str = Field(default="")
    openrouter_model: str = Field(default="")
    huggingface_api_key: str = Field(default="")
    huggingface_model: str = Field(default="meta-llama/Llama-3.1-8B-Instruct")
    llm_max_tokens: int = Field(default=2048)
    llm_temperature: float = Field(default=0.1)
    llm_max_retries: int = Field(default=3)
    llm_retry_delay: float = Field(default=2.0)

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_requests_per_minute: int = Field(default=60)
    rate_limit_burst: int = Field(default=10)

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    log_format: Literal["json", "text"] = Field(default="json")

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        """Ensure the database URL uses the asyncpg driver."""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    @property
    def is_production(self) -> bool:
        """Return True when running in the production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Return True when running in the development environment."""
        return self.environment == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance.

    Uses lru_cache to ensure a single Settings object is created per process,
    preventing repeated environment variable reads.
    """
    return Settings()
