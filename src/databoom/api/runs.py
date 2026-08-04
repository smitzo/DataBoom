"""Generation run execution helpers for the API."""

from __future__ import annotations

from datetime import UTC, datetime
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from databoom.api.models import (
    CollectionArtifactResponse,
    DataProductKind,
    GenerationRunRequest,
    GenerationRunResponse,
    ProductRunRequest,
    RunArtifactListResponse,
    RunArtifactResponse,
    RunStatus,
    TableArtifactResponse,
    ValidationIssueResponse,
    ValidationSummaryResponse,
)
from databoom.api.products import ProductCatalogEntry
from databoom.core.artifacts import ensure_artifact_root
from databoom.core.config import Settings
from databoom.document import DocumentGenerator
from databoom.export import ArtifactExporter, ExportManifest
from databoom.generation import GenerationPlan, create_generation_plan
from databoom.generation.plan import OutputFormat
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


def execute_product_generation_run(
    product: ProductCatalogEntry,
    payload: ProductRunRequest,
    settings: Settings,
) -> GenerationRunResponse:
    """Execute a catalog-backed generation run for the product kind."""

    match product.kind:
        case DataProductKind.RELATIONAL:
            if product.schema_ddl is None:
                raise ValueError("relational product is missing schema DDL")
            return execute_generation_run(
                GenerationRunRequest(
                    schema_ddl=product.schema_ddl,
                    row_counts=payload.row_counts or product.default_counts,
                    seed=payload.seed,
                    domain=product.domain,
                    output_formats=_relational_output_formats(
                        payload.output_formats or product.output_formats
                    ),
                ),
                settings,
            )
        case DataProductKind.DOCUMENT:
            return execute_document_generation_run(product, payload, settings)
        case DataProductKind.GRAPH | DataProductKind.MASKING:
            raise ValueError(f"{product.name} is planned and is not runnable yet")


def execute_document_generation_run(
    product: ProductCatalogEntry,
    payload: ProductRunRequest,
    settings: Settings,
) -> GenerationRunResponse:
    """Execute a synchronous local Docu-Boom generation run."""

    created_at = datetime.now(UTC)
    run_id = uuid4().hex
    artifact_dir = ensure_artifact_root(settings) / "runs" / run_id
    result = DocumentGenerator(
        collections=product.document_collections,
        row_counts=payload.row_counts or product.default_counts,
        seed=payload.seed,
        output_dir=artifact_dir,
    ).generate()

    return GenerationRunResponse(
        run_id=run_id,
        kind=DataProductKind.DOCUMENT,
        status=RunStatus.COMPLETED,
        created_at=created_at,
        completed_at=datetime.now(UTC),
        artifact_dir=artifact_dir,
        manifest_path=result.manifest.manifest_path,
        validation_path=result.validation_path,
        domain=product.domain,
        output_formats=tuple(payload.output_formats or product.output_formats),
        total_rows=result.total_rows,
        table_count=len(result.manifest.collections),
        collections=tuple(
            CollectionArtifactResponse(
                collection_name=collection.collection_name,
                row_count=collection.row_count,
                json_path=collection.json_path,
                ndjson_path=collection.ndjson_path,
            )
            for collection in result.manifest.collections
        ),
        validation=ValidationSummaryResponse(
            passed=bool(result.validation["passed"]),
            checked_tables=tuple(result.validation["checked_collections"]),
            issues=(),
        ),
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
        kind=DataProductKind.RELATIONAL,
        status=RunStatus.COMPLETED if validation.passed else RunStatus.FAILED,
        created_at=created_at,
        completed_at=completed_at,
        artifact_dir=artifact_dir,
        manifest_path=manifest.manifest_path,
        validation_path=validation_path,
        domain=plan.domain,
        output_formats=tuple(str(output_format) for output_format in plan.output_formats),
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


def _relational_output_formats(output_formats: tuple[str, ...]) -> tuple[OutputFormat, ...]:
    formats: list[OutputFormat] = []
    for output_format in output_formats:
        try:
            formats.append(OutputFormat(output_format))
        except ValueError as error:
            raise ValueError(
                f"unsupported relational output format: {output_format}"
            ) from error
    return tuple(formats)
