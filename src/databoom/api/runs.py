"""Generation run execution helpers for the API."""

from __future__ import annotations

from datetime import UTC, datetime
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from databoom.api.models import (
    GenerationRunRequest,
    GenerationRunResponse,
    RunArtifactListResponse,
    RunArtifactResponse,
    RunStatus,
    TableArtifactResponse,
    ValidationIssueResponse,
    ValidationSummaryResponse,
)
from databoom.core.artifacts import ensure_artifact_root
from databoom.core.config import Settings
from databoom.export import ArtifactExporter, ExportManifest
from databoom.generation import GenerationPlan, create_generation_plan
from databoom.ingest import parse_postgres_ddl
from databoom.validation import ValidationReport, validate_export


def execute_generation_run(
    request: GenerationRunRequest,
    settings: Settings,
) -> GenerationRunResponse:
    """Execute a synchronous local generation run."""

    created_at = datetime.now(UTC)
    run_id = uuid4().hex
    artifact_dir = ensure_artifact_root(settings) / "runs" / run_id

    database = parse_postgres_ddl(request.schema_ddl)
    plan = create_generation_plan(
        database,
        row_counts=request.row_counts,
        default_row_count=request.default_row_count,
        seed=request.seed,
        domain=request.domain,
        output_formats=request.output_formats,
    )
    manifest = ArtifactExporter(plan, artifact_dir).export()
    validation = validate_export(plan, manifest)
    validation_path = artifact_dir / "validation.json"
    validation.write_json(validation_path)

    return _completed_response(
        run_id=run_id,
        created_at=created_at,
        completed_at=datetime.now(UTC),
        artifact_dir=artifact_dir,
        plan=plan,
        manifest=manifest,
        validation=validation,
        validation_path=validation_path,
    )


def list_generation_run_artifacts(run: GenerationRunResponse) -> RunArtifactListResponse:
    """Return downloadable files currently present for a generation run."""

    artifact_dir = run.artifact_dir.resolve()
    files: list[RunArtifactResponse] = []

    if artifact_dir.exists():
        for path in sorted(artifact_dir.rglob("*")):
            if path.is_file():
                relative_path = path.relative_to(artifact_dir).as_posix()
                media_type = guess_type(path.name)[0] or "application/octet-stream"
                download_url = f"/runs/{run.run_id}/artifacts/{quote(relative_path, safe='/')}"
                files.append(
                    RunArtifactResponse(
                        name=path.name,
                        relative_path=relative_path,
                        size_bytes=path.stat().st_size,
                        media_type=media_type,
                        download_url=download_url,
                    )
                )

    return RunArtifactListResponse(
        run_id=run.run_id,
        artifact_dir=artifact_dir,
        files=tuple(files),
    )


def resolve_generation_run_artifact(run: GenerationRunResponse, artifact_path: str) -> Path:
    """Resolve one artifact path while keeping access inside the run directory."""

    artifact_dir = run.artifact_dir.resolve()
    requested_path = (artifact_dir / artifact_path).resolve()

    if not requested_path.is_relative_to(artifact_dir):
        raise ValueError("artifact path is outside run directory")
    if not requested_path.is_file():
        raise FileNotFoundError(artifact_path)
    return requested_path


def _completed_response(
    *,
    run_id: str,
    created_at: datetime,
    completed_at: datetime,
    artifact_dir,
    plan: GenerationPlan,
    manifest: ExportManifest,
    validation: ValidationReport,
    validation_path,
) -> GenerationRunResponse:
    return GenerationRunResponse(
        run_id=run_id,
        status=RunStatus.COMPLETED if validation.passed else RunStatus.FAILED,
        created_at=created_at,
        completed_at=completed_at,
        artifact_dir=artifact_dir,
        manifest_path=manifest.manifest_path,
        validation_path=validation_path,
        domain=plan.domain,
        output_formats=plan.output_formats,
        total_rows=plan.total_rows,
        table_count=len(plan.tables),
        tables=tuple(
            TableArtifactResponse(
                table_name=table.table_name,
                row_count=table.row_count,
                csv_path=table.csv_path,
                json_path=table.json_path,
                sql_path=table.sql_path,
            )
            for table in manifest.tables
        ),
        validation=ValidationSummaryResponse(
            passed=validation.passed,
            checked_tables=validation.checked_tables,
            issues=tuple(
                ValidationIssueResponse(
                    code=issue.code,
                    message=issue.message,
                    table_name=issue.table_name,
                )
                for issue in validation.issues
            ),
        ),
    )
