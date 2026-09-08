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
