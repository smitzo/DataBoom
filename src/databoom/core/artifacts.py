"""Local artifact path helpers."""

from __future__ import annotations

from pathlib import Path

from databoom.core.config import Settings


def ensure_artifact_root(settings: Settings) -> Path:
    """Create and return the configured artifact root directory."""

    artifact_root = settings.resolve_artifact_root()
    artifact_root.mkdir(parents=True, exist_ok=True)
    return artifact_root
