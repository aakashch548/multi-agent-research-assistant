"""Application configuration using pydantic-settings.

Loads settings from environment variables and .env file with full
validation, computed properties, and sensible defaults for all
deployment environments.
"""

from __future__ import annotations

import json
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(StrEnum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Central application settings loaded from environment / .env file.

    All fields support override via environment variables. The .env file
    is resolved relative to this module's parent directory (``backend/``).
    """

    _OPENAI_PLACEHOLDERS = frozenset({"demo-key", "sk-your-key-here", "sk-test"})
    _TAVILY_PLACEHOLDERS = frozenset({"demo-key", "tvly-your-key-here"})

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- OpenAI ---
    openai_api_key: str = Field(
        default="", description="OpenAI API key for LLM calls"
    )
    openai_model: str = Field(
        default="gpt-4o", description="Default OpenAI chat model"
    )

    # --- Tavily ---
    tavily_api_key: str = Field(
        default="", description="Tavily API key for web search"
    )

    # --- Demo mode ---
    demo_mode: bool = Field(
        default=False,
        description="Run with mock data instead of external API calls",
    )

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/research_db",
        description="Async SQLAlchemy database URL",
    )

    # --- Redis ---
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # --- ChromaDB ---
    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8000)
    chroma_collection: str = Field(default="research_documents")

    # --- Logging ---
    log_level: LogLevel = Field(default=LogLevel.INFO)
    environment: Environment = Field(default=Environment.DEVELOPMENT)

    # --- API ---
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    frontend_url: str = Field(default="http://localhost:8501")
    cors_origins: list[str] = Field(
        default=["http://localhost:8501", "http://localhost:3000"]
    )

    # --- Agent orchestration ---
    max_concurrent_agents: int = Field(
        default=5, ge=1, le=50,
        description="Maximum number of agents executing in parallel",
    )
    agent_timeout_seconds: int = Field(
        default=120, ge=10, le=600,
        description="Per-agent execution timeout",
    )

    # --- RAG / Embeddings ---
    chunk_size: int = Field(default=1000, ge=100, le=10_000)
    chunk_overlap: int = Field(default=200, ge=0)
    embedding_model: str = Field(default="text-embedding-3-small")

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Accept JSON-encoded string or native list."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("database_url", mode="after")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure the database URL uses an async driver."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "Settings":
        """chunk_overlap must be strictly less than chunk_size."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be less than "
                f"chunk_size ({self.chunk_size})"
            )
        if not self.demo_mode:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when DEMO_MODE is disabled")
            if not self.tavily_api_key:
                raise ValueError("TAVILY_API_KEY is required when DEMO_MODE is disabled")
        return self

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------

    @property
    def has_openai(self) -> bool:
        """True when a real (non-placeholder) OpenAI key is configured."""
        key = (self.openai_api_key or "").strip()
        return bool(key and key not in self._OPENAI_PLACEHOLDERS)

    @property
    def has_tavily(self) -> bool:
        """True when a real (non-placeholder) Tavily key is configured."""
        key = (self.tavily_api_key or "").strip()
        return bool(key and key not in self._TAVILY_PLACEHOLDERS)

    @property
    def use_offline_mode(self) -> bool:
        """Use mock/demo agent data when demo mode is on or API keys are missing."""
        return self.demo_mode or not self.has_openai

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING

    @property
    def sync_database_url(self) -> str:
        """Return a synchronous variant of the database URL (for Alembic)."""
        return self.database_url.replace("+asyncpg", "")

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"

    @property
    def db_host(self) -> str:
        """Extract the host component from the database URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.database_url.replace("+asyncpg", ""))
        return parsed.hostname or "localhost"

    @property
    def db_port(self) -> int:
        """Extract the port component from the database URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.database_url.replace("+asyncpg", ""))
        return parsed.port or 5432

    @property
    def db_name(self) -> str:
        """Extract the database name from the database URL."""
        from urllib.parse import urlparse
        parsed = urlparse(self.database_url.replace("+asyncpg", ""))
        return (parsed.path or "/research_db").lstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()
