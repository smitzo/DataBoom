"""Generation run execution helpers for the API.

Purpose:
    Convert API product requests into concrete Table-Boom or Docu-Boom generation
    runs and API response payloads.

Data flow:
    request payload -> source/schema/profile resolution -> generation plan or
    document spec -> artifact export -> validation -> `GenerationRunResponse`.

Why this layer exists:
    Routes should validate HTTP concerns and delegate execution. This module keeps
    backend run orchestration reusable by sync routes, async workers, tests, and
    future CLI/API shared workflows.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from mimetypes import guess_type
from pathlib import Path
from time import perf_counter
from urllib.parse import quote
from uuid import uuid4

from databoom.api.models import (
    CollectionArtifactResponse,
    DataProductKind,
    GenerationRunRequest,
    GenerationRunResponse,
    OperationStatus,
    OperationTimingResponse,
    ProductRunRequest,
    RelationshipFanoutMetricResponse,
    RunArtifactListResponse,
    RunArtifactResponse,
    RunStatus,
    TableArtifactResponse,
    ValidationIssueResponse,
    ValidationSummaryResponse,
)
from databoom.api.products import ProductCatalogEntry
from databoom.api.workspaces import WorkspaceSource, get_workspace_source
from databoom.core.artifacts import ensure_artifact_root
from databoom.core.config import Settings
from databoom.document import DocumentCollectionSpec, DocumentFieldSpec, DocumentGenerator
from databoom.export import ArtifactExporter, ExportManifest
from databoom.generation import (
    ChildCountFrequency,
    ColumnProfileHint,
    ForeignKeySelectionStrategy,
    GenerationPlan,
    RelationshipFanoutHint,
    TopValueHint,
    create_generation_plan,
)
from databoom.generation.plan import OutputFormat
from databoom.ingest import parse_postgres_ddl
from databoom.profiling import SourceProfile
from databoom.validation import ValidationReport, validate_export

RunProgressCallback = Callable[[int, str], None]


def execute_generation_run(
    request: GenerationRunRequest,
    settings: Settings,
    *,
    run_id: str | None = None,
    created_at: datetime | None = None,
    artifact_dir: Path | None = None,
    progress_callback: RunProgressCallback | None = None,
    foreign_key_strategy: ForeignKeySelectionStrategy | None = None,
    relationship_hints: tuple[RelationshipFanoutHint, ...] = (),
    column_hints: tuple[ColumnProfileHint, ...] = (),
) -> GenerationRunResponse:
    """Execute a synchronous local Table-Boom generation run.

    Stages are timed separately so the dashboard can explain whether time was
    spent parsing schema, building the plan, exporting files, or validating output.
    """

    created_at = created_at or datetime.now(UTC)
    run_id = run_id or uuid4().hex
    artifact_dir = artifact_dir or ensure_artifact_root(settings) / "runs" / run_id
    timings: list[OperationTimingResponse] = []

    parse_started = _started_at()
    database = parse_postgres_ddl(request.schema_ddl)
    timings.append(_completed_timing("parse_schema", parse_started))

    plan_started = _started_at()
    # Relationship hints come from source profiling. When they are present, prefer
    # profile-driven fanout; otherwise use balanced fanout for stable coverage.
    effective_foreign_key_strategy = foreign_key_strategy or (
        ForeignKeySelectionStrategy.PROFILE_DRIVEN
        if relationship_hints
        else ForeignKeySelectionStrategy.BALANCED_FANOUT
    )
    plan = create_generation_plan(
        database,
        row_counts=request.row_counts,
        default_row_count=request.default_row_count,
        seed=request.seed,
        domain=request.domain,
        output_formats=request.output_formats,
        foreign_key_strategy=effective_foreign_key_strategy,
        relationship_hints=relationship_hints,
        column_hints=column_hints,
    )
    timings.append(_completed_timing("build_plan", plan_started))

    export_started = _started_at()
    manifest = ArtifactExporter(
        plan,
        artifact_dir,
        progress_callback=progress_callback,
    ).export()
    timings.append(_completed_timing("export_artifacts", export_started))

    validation_started = _started_at()
    validation = validate_export(plan, manifest)
    timings.append(_completed_timing("validate_artifacts", validation_started))
    validation_path = artifact_dir / "validation.json"
    validation.write_json(validation_path)
    completed_at = datetime.now(UTC)
    timings.append(_elapsed_timing("total_run", created_at, completed_at))

    return _completed_response(
        run_id=run_id,
        created_at=created_at,
        completed_at=completed_at,
        artifact_dir=artifact_dir,
        plan=plan,
        manifest=manifest,
        validation=validation,
        validation_path=validation_path,
        operation_timings=tuple(timings),
    )


def execute_product_generation_run(
    product: ProductCatalogEntry,
    payload: ProductRunRequest,
    settings: Settings,
    *,
    source: WorkspaceSource | None = None,
    source_profile: SourceProfile | None = None,
    run_id: str | None = None,
    created_at: datetime | None = None,
    artifact_dir: Path | None = None,
    progress_callback: RunProgressCallback | None = None,
) -> GenerationRunResponse:
    """Execute a catalog-backed generation run for the selected product kind."""

    source = _source_for_payload(product, payload, source)
    match product.kind:
        case DataProductKind.RELATIONAL:
            schema_ddl = _schema_ddl_for_source(source) if source else product.schema_ddl
            if schema_ddl is None:
                raise ValueError("relational product is missing schema DDL")
            # Source profiles are optional. If no profile exists, plan creation and
            # value generation keep deterministic fallback behavior.
            relationship_hints = _relationship_hints_from_source_profile(source_profile)
            column_hints = _column_hints_from_source_profile(source_profile)
            return execute_generation_run(
                GenerationRunRequest(
                    schema_ddl=schema_ddl,
                    row_counts=payload.row_counts
                    or _source_default_counts(source)
                    or product.default_counts,
                    seed=payload.seed,
                    domain=product.domain,
                    output_formats=_relational_output_formats(
                        payload.output_formats or product.output_formats
                    ),
                ),
                settings,
                run_id=run_id,
                created_at=created_at,
                artifact_dir=artifact_dir,
                progress_callback=progress_callback,
                relationship_hints=relationship_hints,
                column_hints=column_hints,
            )
        case DataProductKind.DOCUMENT:
            return execute_document_generation_run(
                product,
                payload,
                settings,
                source=source,
                run_id=run_id,
                created_at=created_at,
                artifact_dir=artifact_dir,
                progress_callback=progress_callback,
            )
        case DataProductKind.GRAPH | DataProductKind.MASKING:
            raise ValueError(f"{product.name} is planned and is not runnable yet")


def execute_document_generation_run(
    product: ProductCatalogEntry,
    payload: ProductRunRequest,
    settings: Settings,
    *,
    source: WorkspaceSource | None = None,
    run_id: str | None = None,
    created_at: datetime | None = None,
    artifact_dir: Path | None = None,
    progress_callback: RunProgressCallback | None = None,
) -> GenerationRunResponse:
    """Execute a synchronous local Docu-Boom generation run."""

    created_at = created_at or datetime.now(UTC)
    run_id = run_id or uuid4().hex
    artifact_dir = artifact_dir or ensure_artifact_root(settings) / "runs" / run_id
    generation_started = _started_at()
    collections = (
        _document_collections_for_source(source) if source else product.document_collections
    )
    row_counts = payload.row_counts or _source_default_counts(source) or product.default_counts
    result = DocumentGenerator(
        collections=collections,
        row_counts=row_counts,
        seed=payload.seed,
        output_dir=artifact_dir,
        progress_callback=progress_callback,
    ).generate()
    completed_at = datetime.now(UTC)
    total_seconds = max((completed_at - created_at).total_seconds(), 0.0)

    return GenerationRunResponse(
        run_id=run_id,
        kind=DataProductKind.DOCUMENT,
        status=RunStatus.COMPLETED,
        created_at=created_at,
        completed_at=completed_at,
        artifact_dir=artifact_dir,
        manifest_path=result.manifest.manifest_path,
        validation_path=result.validation_path,
        domain=product.domain,
        output_formats=tuple(payload.output_formats or product.output_formats),
        total_rows=result.total_rows,
        table_count=len(result.manifest.collections),
        generated_rows=result.total_rows,
        progress_percent=100.0,
        rows_per_second=_rows_per_second(result.total_rows, total_seconds),
        operation_timings=(
            _completed_timing("generate_documents", generation_started),
            _elapsed_timing("total_run", created_at, completed_at),
        ),
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


def _source_for_payload(
    product: ProductCatalogEntry,
    payload: ProductRunRequest,
    source: WorkspaceSource | None = None,
) -> WorkspaceSource | None:
    if source is not None:
        if payload.source_id is not None and payload.source_id != source.id:
            raise ValueError("workspace source does not match request")
        if source.product_id != product.id or source.kind != product.kind:
            raise ValueError("workspace source is not compatible with this product")
        return source
    if payload.source_id is None:
        return None
    try:
        source = get_workspace_source(payload.source_id)
    except KeyError as error:
        raise ValueError("workspace source not found") from error
    if source.product_id != product.id or source.kind != product.kind:
        raise ValueError("workspace source is not compatible with this product")
    return source


def _source_default_counts(source: WorkspaceSource | None) -> dict[str, int]:
    if source is None:
        return {}
    return {resource.name: resource.estimated_rows for resource in source.resources}


def _schema_ddl_for_source(source: WorkspaceSource | None) -> str | None:
    if source is None:
        return None
    if source.schema_ddl:
        return source.schema_ddl
    statements = []
    for resource in source.resources:
        columns = resource.columns or ("id", "name", "status")
        column_definitions = [_column_definition(column) for column in columns]
        if "id" not in columns:
            column_definitions.insert(0, "id bigint PRIMARY KEY")
        columns_sql = ",\n    ".join(column_definitions)
        statements.append(
            "CREATE TABLE "
            f"{_sql_identifier(resource.name)} (\n"
            f"    {columns_sql}\n"
            ");"
        )
    return "\n\n".join(statements)


def _document_collections_for_source(
    source: WorkspaceSource | None,
) -> tuple[DocumentCollectionSpec, ...]:
    if source is None:
        return ()
    return tuple(
        DocumentCollectionSpec(
            name=resource.name,
            default_count=resource.estimated_rows,
            fields=tuple(
                _document_field(column)
                for column in resource.columns or ("_id", "status")
            ),
        )
        for resource in source.resources
    )


def _column_definition(column: str) -> str:
    quoted = _sql_identifier(column)
    if column == "id":
        return f"{quoted} bigint PRIMARY KEY"
    if column == "_id":
        return f"{quoted} text PRIMARY KEY"
    if column.endswith("_id"):
        return f"{quoted} bigint NOT NULL"
    if column in {"amount", "balance", "total", "price", "payment_amount", "value"}:
        return f"{quoted} numeric NOT NULL"
    if column in {"age", "quantity"}:
        return f"{quoted} integer NOT NULL"
    if column.endswith("_at") or column in {"posted_at", "created_at"}:
        return f"{quoted} timestamp"
    if column in {"dob"}:
        return f"{quoted} date"
    return f"{quoted} text"


def _document_field(column: str) -> DocumentFieldSpec:
    if column == "_id":
        return DocumentFieldSpec(column, "object_id")
    if column.endswith("_id"):
        return DocumentFieldSpec(column, "reference")
    if column == "email":
        return DocumentFieldSpec(column, "email")
    if column in {"amount", "balance", "total", "price", "value"}:
        return DocumentFieldSpec(column, "money")
    if column in {"age", "quantity"}:
        return DocumentFieldSpec(column, "integer")
    if column.endswith("_at"):
        return DocumentFieldSpec(column, "timestamp")
    if column in {"profile", "metadata", "coverage"}:
        return DocumentFieldSpec(
            column,
            "object",
            fields=(
                DocumentFieldSpec("label", "text"),
                DocumentFieldSpec("status", "status"),
            ),
        )
    if column in {"items"}:
        return DocumentFieldSpec(
            column,
            "array",
            item_fields=(
                DocumentFieldSpec("name", "product_name"),
                DocumentFieldSpec("quantity", "quantity"),
            ),
        )
    if column == "status":
        return DocumentFieldSpec(column, "status")
    return DocumentFieldSpec(column, "text")


def _sql_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


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
    operation_timings: tuple[OperationTimingResponse, ...] = (),
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
        generated_rows=plan.total_rows,
        progress_percent=100.0,
        rows_per_second=_rows_per_second(
            plan.total_rows,
            _total_timing_seconds(operation_timings),
        ),
        operation_timings=operation_timings,
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
            relationship_metrics=_relationship_metric_responses(validation),
        ),
    )


def _relationship_metric_responses(
    validation: ValidationReport,
) -> tuple[RelationshipFanoutMetricResponse, ...]:
    return tuple(
        RelationshipFanoutMetricResponse(
            child_table=metric.child_table,
            child_columns=metric.child_columns,
            parent_table=metric.parent_table,
            parent_columns=metric.parent_columns,
            parent_key_count=metric.parent_key_count,
            child_row_count=metric.child_row_count,
            min_children_per_parent=metric.min_children_per_parent,
            max_children_per_parent=metric.max_children_per_parent,
            average_children_per_parent=metric.average_children_per_parent,
            empty_parent_count=metric.empty_parent_count,
        )
        for metric in validation.relationship_metrics
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


def _relationship_hints_from_source_profile(
    source_profile: SourceProfile | None,
) -> tuple[RelationshipFanoutHint, ...]:
    if source_profile is None:
        return ()

    return tuple(
        RelationshipFanoutHint(
            child_table=_qualified_table(relationship.child_schema, relationship.child_table),
            child_columns=relationship.child_columns,
            parent_table=_qualified_table(relationship.parent_schema, relationship.parent_table),
            parent_columns=relationship.parent_columns,
            child_count_frequencies=tuple(
                ChildCountFrequency(
                    child_count=frequency.child_count,
                    parent_frequency=frequency.parent_frequency,
                )
                for frequency in relationship.child_count_frequencies
            ),
        )
        for relationship in source_profile.relationships
    )


def _column_hints_from_source_profile(
    source_profile: SourceProfile | None,
) -> tuple[ColumnProfileHint, ...]:
    """Convert stored source profiles into generation-plan column hints."""

    if source_profile is None:
        return ()

    return tuple(
        ColumnProfileHint(
            table_name=_qualified_table(table.schema_name, table.name),
            column_name=column.name,
            sample_count=column.row_count,
            null_rate=column.null_rate,
            distinct_count=column.distinct_count,
            min_value=column.min_value,
            max_value=column.max_value,
            top_values=tuple(
                TopValueHint(value=top_value.value, count=top_value.count)
                for top_value in column.top_values
            ),
        )
        for table in source_profile.tables
        for column in table.columns
    )


def _qualified_table(schema_name: str, table_name: str) -> str:
    return f"{schema_name}.{table_name}"


def _started_at() -> tuple[datetime, float]:
    return datetime.now(UTC), perf_counter()


def _completed_timing(
    operation: str,
    started: tuple[datetime, float],
) -> OperationTimingResponse:
    started_at, started_counter = started
    completed_at = datetime.now(UTC)
    return OperationTimingResponse(
        operation=operation,
        status=OperationStatus.COMPLETED,
        elapsed_seconds=round(max(perf_counter() - started_counter, 0.0), 3),
        started_at=started_at,
        completed_at=completed_at,
    )


def _elapsed_timing(
    operation: str,
    started_at: datetime,
    completed_at: datetime,
) -> OperationTimingResponse:
    return OperationTimingResponse(
        operation=operation,
        status=OperationStatus.COMPLETED,
        elapsed_seconds=round(max((completed_at - started_at).total_seconds(), 0.0), 3),
        started_at=started_at,
        completed_at=completed_at,
    )


def _total_timing_seconds(operation_timings: tuple[OperationTimingResponse, ...]) -> float | None:
    total_timing = next(
        (timing for timing in operation_timings if timing.operation == "total_run"),
        None,
    )
    return total_timing.elapsed_seconds if total_timing is not None else None


def _rows_per_second(total_rows: int, seconds: float | None) -> float | None:
    if seconds is None or seconds <= 0:
        return None
    return round(total_rows / seconds, 2)
