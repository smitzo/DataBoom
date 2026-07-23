"""Generation run execution helpers for the API."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from boom_data.api.models import (
    GenerationRunRequest,
    GenerationRunResponse,
    RunStatus,
    TableArtifactResponse,
    ValidationIssueResponse,
    ValidationSummaryResponse,
)
from boom_data.core.artifacts import ensure_artifact_root
from boom_data.core.config import Settings
from boom_data.export import ArtifactExporter, ExportManifest
from boom_data.generation import GenerationPlan, create_generation_plan
from boom_data.ingest import parse_postgres_ddl
from boom_data.validation import ValidationReport, validate_export


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
