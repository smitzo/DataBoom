"""HTTP routes for the Boom Data API."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Request, status

from boom_data import __version__
from boom_data.api.models import GenerationRunRequest, GenerationRunResponse, HealthResponse
from boom_data.api.runs import execute_generation_run
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


@router.post(
    "/runs",
    response_model=GenerationRunResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["runs"],
)
def create_run(request: Request, payload: GenerationRunRequest) -> GenerationRunResponse:
    """Execute a local relational generation run and store the run result."""

    settings: Settings = request.app.state.settings
    try:
        run = execute_generation_run(payload, settings)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    _run_store(request)[run.run_id] = run
    return run


@router.get("/runs", response_model=tuple[GenerationRunResponse, ...], tags=["runs"])
def list_runs(request: Request) -> tuple[GenerationRunResponse, ...]:
    """Return known generation runs for the current API process."""

    return tuple(_run_store(request).values())


@router.get("/runs/{run_id}", response_model=GenerationRunResponse, tags=["runs"])
def get_run(request: Request, run_id: str) -> GenerationRunResponse:
    """Return one generation run by ID."""

    run = _run_store(request).get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return run


def _run_store(request: Request) -> dict[str, GenerationRunResponse]:
    return cast("dict[str, GenerationRunResponse]", request.app.state.run_store)
