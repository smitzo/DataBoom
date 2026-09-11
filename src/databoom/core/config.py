"""Runtime configuration for DataBoom.

Purpose:
    Load environment-driven settings shared by the CLI, API, and Docker runtime.

Data flow:
    environment variables or `.env` -> `Settings` -> app factory, CLI commands,
    artifact helpers, and state-store creation.

Why this layer exists:
    Runtime choices should be configured at the boundary of the process, not
    hardcoded inside generation or API modules.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    environment: str = Field(default="local", validation_alias=AliasChoices("DATABOOM_ENV", "ENV"))
    artifact_root: Path = Field(
        default=Path("artifacts"),
        validation_alias=AliasChoices("DATABOOM_ARTIFACT_ROOT", "ARTIFACT_ROOT"),
    )
    database_url: str = Field(
        default="postgresql+psycopg://databoom:databoom@localhost:5432/databoom",
        validation_alias=AliasChoices("DATABOOM_DATABASE_URL", "DATABASE_URL"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("DATABOOM_REDIS_URL", "REDIS_URL"),
    )
    api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABOOM_API_KEY", "API_KEY"),
    )
    seed_login_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABOOM_SEED_LOGIN_ID", "SEED_LOGIN_ID"),
    )
    seed_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABOOM_SEED_EMAIL", "SEED_EMAIL"),
    )
    seed_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABOOM_SEED_NAME", "SEED_NAME"),
    )
    seed_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABOOM_SEED_PASSWORD", "SEED_PASSWORD"),
    )
    allow_registration: bool = Field(
        default=True,
        validation_alias=AliasChoices("DATABOOM_ALLOW_REGISTRATION", "ALLOW_REGISTRATION"),
    )
    supabase_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABOOM_SUPABASE_URL", "SUPABASE_URL"),
    )
    supabase_anon_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABOOM_SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY"),
    )
    llm_platform_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABOOM_LLM_PLATFORM_API_KEY", "OPENAI_API_KEY"),
    )
    llm_default_model: str = Field(
        default="gpt-4.1-mini",
        validation_alias=AliasChoices("DATABOOM_LLM_DEFAULT_MODEL", "LLM_DEFAULT_MODEL"),
    )
    llm_request_token_limit: int = Field(
        default=4_000,
        ge=256,
        validation_alias=AliasChoices(
            "DATABOOM_LLM_REQUEST_TOKEN_LIMIT",
            "LLM_REQUEST_TOKEN_LIMIT",
        ),
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("DATABOOM_LOG_LEVEL", "LOG_LEVEL"),
    )
    cors_origins: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ),
        validation_alias=AliasChoices("DATABOOM_CORS_ORIGINS", "CORS_ORIGINS"),
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Store log levels consistently for logging configuration."""

        return value.upper()

    @field_validator("api_key", mode="before")
    @classmethod
    def empty_api_key_is_unset(cls, value: object) -> object:
        """Treat empty environment values as disabled API-key authentication."""

        if value == "":
            return None
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        """Route hosted Postgres URLs through the installed psycopg driver."""

        if isinstance(value, str) and value.startswith("postgres://"):
            return f"postgresql+psycopg://{value.removeprefix('postgres://')}"
        if isinstance(value, str) and value.startswith("postgresql://"):
            return f"postgresql+psycopg://{value.removeprefix('postgresql://')}"
        return value

    @field_validator(
        "seed_login_id",
        "seed_email",
        "seed_name",
        "seed_password",
        "supabase_url",
        "supabase_anon_key",
        "llm_platform_api_key",
        mode="before",
    )
    @classmethod
    def empty_optional_settings_are_unset(cls, value: object) -> object:
        """Treat empty deployment environment values as unset."""

        if value == "":
            return None
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        """Support comma-separated CORS origins from environment variables."""

        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        return value

    def resolve_artifact_root(self) -> Path:
        """Return the artifact root as an absolute path without creating it."""

        return self.artifact_root.expanduser().resolve()


@lru_cache
def get_settings(log_level: str | None = None) -> Settings:
    """Return cached settings, with an optional CLI log-level override."""

    settings = Settings()
    if log_level is None:
        return settings
    return settings.model_copy(update={"log_level": log_level.upper()})
