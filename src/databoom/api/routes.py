"""HTTP routes for the DataBoom API."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from databoom import __version__
from databoom.api.models import (
    GenerationRunRequest,
    GenerationRunResponse,
    HealthResponse,
    RunArtifactListResponse,
)
from databoom.api.runs import (
    execute_generation_run,
    list_generation_run_artifacts,
    resolve_generation_run_artifact,
)
from databoom.api.security import require_api_key
from databoom.core.config import Settings

router = APIRouter()
protected_route = Depends(require_api_key)


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request) -> HealthResponse:
    """Return service health and resolved runtime context."""

    settings: Settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service="databoom-api",
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
    dependencies=[protected_route],
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


@router.get(
    "/runs",
    response_model=tuple[GenerationRunResponse, ...],
    tags=["runs"],
    dependencies=[protected_route],
)
def list_runs(request: Request) -> tuple[GenerationRunResponse, ...]:
    """Return known generation runs for the current API process."""

    return tuple(_run_store(request).values())


@router.get(
    "/runs/{run_id}",
    response_model=GenerationRunResponse,
    tags=["runs"],
    dependencies=[protected_route],
)
def get_run(request: Request, run_id: str) -> GenerationRunResponse:
    """Return one generation run by ID."""

    return _get_existing_run(request, run_id)


@router.get(
    "/runs/{run_id}/artifacts",
    response_model=RunArtifactListResponse,
    tags=["runs"],
    dependencies=[protected_route],
)
def list_run_artifacts(request: Request, run_id: str) -> RunArtifactListResponse:
    """Return downloadable artifacts for one generation run."""

    run = _get_existing_run(request, run_id)
    return list_generation_run_artifacts(run)


@router.get(
    "/runs/{run_id}/artifacts/{artifact_path:path}",
    tags=["runs"],
    dependencies=[protected_route],
)
def download_run_artifact(request: Request, run_id: str, artifact_path: str) -> FileResponse:
    """Download one generated artifact from a run directory."""

    run = _get_existing_run(request, run_id)
    try:
        path = resolve_generation_run_artifact(run, artifact_path)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="artifact not found",
        ) from error

    return FileResponse(path, filename=path.name)


def _run_store(request: Request) -> dict[str, GenerationRunResponse]:
    return cast("dict[str, GenerationRunResponse]", request.app.state.run_store)


def _get_existing_run(request: Request, run_id: str) -> GenerationRunResponse:
    run = _run_store(request).get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return run
