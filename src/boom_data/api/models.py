"""API response models."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Health payload returned by the API service."""

    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    version: str
    environment: str
    artifact_root: Path
