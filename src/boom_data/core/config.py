"""Runtime configuration for Boom Data."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BOOM_DATA_",
        extra="ignore",
    )

    environment: str = Field(default="local", alias="ENV")
    artifact_root: Path = Field(default=Path("artifacts"), alias="ARTIFACT_ROOT")
    database_url: str = Field(
        default="postgresql+psycopg://boom_data:boom_data@localhost:5432/boom_data",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    api_key: SecretStr | None = Field(default=None, alias="API_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

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
