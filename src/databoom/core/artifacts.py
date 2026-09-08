"""Local artifact path helpers.

Purpose:
    Centralize where generated manifests, exports, validation reports, and run
    artifacts are written.

Why this layer exists:
    API, CLI, and async workers should agree on artifact roots instead of each
    constructing paths independently.
"""

from __future__ import annotations

from pathlib import Path

from databoom.core.config import Settings


def ensure_artifact_root(settings: Settings) -> Path:
    """Create and return the configured artifact root directory."""

    artifact_root = settings.resolve_artifact_root()
    artifact_root.mkdir(parents=True, exist_ok=True)
    return artifact_root
