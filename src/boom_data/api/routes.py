"""HTTP routes for the Boom Data API."""

from __future__ import annotations

from fastapi import APIRouter, Request

from boom_data import __version__
from boom_data.api.models import HealthResponse
from boom_data.core.config import Settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request) -> HealthResponse:
    """Return service health and resolved runtime context."""

    settings: Settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service="boom-data-api",
        version=__version__,
        environment=settings.environment,
        artifact_root=settings.resolve_artifact_root(),
    )


@router.get("/ready", response_model=HealthResponse, tags=["system"])
def ready(request: Request) -> HealthResponse:
    """Return readiness for the current single-process API service."""

    return health(request)
