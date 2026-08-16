"""In-process async run manager for local API generation."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Lock
from uuid import uuid4

from databoom.api.models import (
    CollectionArtifactResponse,
    DataProductKind,
    GenerationRunResponse,
    OperationStatus,
    OperationTimingResponse,
    ProductRunRequest,
    RunStatus,
    TableArtifactResponse,
)
from databoom.api.products import ProductCatalogEntry
from databoom.api.runs import (
    _document_collections_for_source,
    _schema_ddl_for_source,
    _source_default_counts,
    _source_for_payload,
    execute_product_generation_run,
)
from databoom.api.state import StateStore
from databoom.api.workspaces import WorkspaceSource
from databoom.core.artifacts import ensure_artifact_root
from databoom.core.config import Settings
from databoom.generation import create_generation_plan
from databoom.generation.plan import OutputFormat
from databoom.ingest import parse_postgres_ddl

BASELINE_RECORDS_PER_SECOND = 500_000 / 233.707


class RunControlError(ValueError):
    """Raised when a run cannot accept the requested control action."""


class RunNotFoundError(KeyError):
    """Raised when the async manager does not know a requested run."""


class RunCancelledError(Exception):
    """Internal cooperative cancellation signal for background runs."""


@dataclass
class RunProgressState:
    """Latest observed row progress for one background run."""

    generated_rows: int = 0
    current_resource: str | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class ProductRunContext:
    """Original async product-run inputs needed for retries."""

    product: ProductCatalogEntry
    payload: ProductRunRequest
    retry_of_run_id: str | None = None


@dataclass
class AsyncRunManager:
    """Track background generation runs for the local API process."""

    max_workers: int = 2
    executor: ThreadPoolExecutor = field(init=False)
    _runs: dict[str, GenerationRunResponse] = field(default_factory=dict, init=False)
    _progress: dict[str, RunProgressState] = field(default_factory=dict, init=False)
    _contexts: dict[str, ProductRunContext] = field(default_factory=dict, init=False)
    _futures: dict[str, Future[None]] = field(default_factory=dict, init=False)
    _cancel_events: dict[str, Event] = field(default_factory=dict, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    def __post_init__(self) -> None:
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="databoom-run",
        )

    def submit_product_run(
        self,
        *,
        product: ProductCatalogEntry,
        payload: ProductRunRequest,
        settings: Settings,
        state_store: StateStore,
        retry_of_run_id: str | None = None,
    ) -> GenerationRunResponse:
        """Create a running placeholder and execute the product run in the background."""

        created_at = datetime.now(UTC)
        run_id = uuid4().hex
        artifact_dir = ensure_artifact_root(settings) / "runs" / run_id
        cancel_event = Event()
        placeholder = _running_product_response(
            product=product,
            payload=payload,
            run_id=run_id,
            created_at=created_at,
            artifact_dir=artifact_dir,
            retry_of_run_id=retry_of_run_id,
        )
        self._register_run(
            placeholder,
            ProductRunContext(product=product, payload=payload, retry_of_run_id=retry_of_run_id),
            cancel_event,
        )
        state_store.save_run(placeholder)
        future = self.executor.submit(
            self._execute_product_run,
            product,
            payload,
            settings,
            state_store,
            run_id,
            created_at,
            artifact_dir,
            cancel_event,
            retry_of_run_id,
        )
        with self._lock:
            self._futures[run_id] = future
        return self.get_run(run_id) or placeholder

    def get_run(self, run_id: str) -> GenerationRunResponse | None:
        """Return current in-memory run state with dynamic running progress."""

        with self._lock:
            run = self._runs.get(run_id)
            progress = self._progress.get(run_id, RunProgressState())
        if run is None:
            return None
        if run.status != RunStatus.RUNNING:
            return run
        return _with_running_progress(run, progress)

    def cancel_run(self, run_id: str, state_store: StateStore) -> GenerationRunResponse:
        """Request cooperative cancellation for a running background run."""

        with self._lock:
            run = self._runs.get(run_id)
            progress = self._progress.get(run_id, RunProgressState())
            cancel_event = self._cancel_events.get(run_id)
            future = self._futures.get(run_id)

        if run is None:
            raise RunNotFoundError(run_id)
        if run.status != RunStatus.RUNNING:
            raise RunControlError(
                f"only running runs can be canceled; current status is {run.status}"
            )

        if cancel_event is not None:
            cancel_event.set()
        if future is not None:
            future.cancel()

        canceled = _canceled_response(run, progress)
        self._set_run(canceled)
        state_store.save_run(canceled)
        return canceled

    def retry_run(
        self,
        run_id: str,
        *,
        settings: Settings,
        state_store: StateStore,
    ) -> GenerationRunResponse:
        """Start a new async run from a failed or canceled run's original request."""

        with self._lock:
            run = self._runs.get(run_id)
            context = self._contexts.get(run_id)

        if run is None:
            raise RunNotFoundError(run_id)
        if run.status not in {RunStatus.FAILED, RunStatus.CANCELED}:
            raise RunControlError(
                f"only failed or canceled runs can be retried; current status is {run.status}"
            )
        if context is None:
            raise RunControlError("run retry context is unavailable")

        return self.submit_product_run(
            product=context.product,
            payload=context.payload,
            settings=settings,
            state_store=state_store,
            retry_of_run_id=run_id,
        )

    def shutdown(self) -> None:
        """Release background worker threads when the API application stops."""

        self.executor.shutdown(wait=False, cancel_futures=False)

    def _execute_product_run(
        self,
        product: ProductCatalogEntry,
        payload: ProductRunRequest,
        settings: Settings,
        state_store: StateStore,
        run_id: str,
        created_at: datetime,
        artifact_dir: Path,
        cancel_event: Event,
        retry_of_run_id: str | None,
    ) -> None:
        try:
            _raise_if_canceled(cancel_event)
            run = execute_product_generation_run(
                product,
                payload,
                settings,
                run_id=run_id,
                created_at=created_at,
                artifact_dir=artifact_dir,
                progress_callback=lambda generated_rows, current_resource: self._update_progress(
                    run_id,
                    generated_rows,
                    current_resource,
                    cancel_event,
                ),
            )
            if retry_of_run_id is not None:
                run = run.model_copy(update={"retry_of_run_id": retry_of_run_id})
            if cancel_event.is_set():
                run = _canceled_response(run, self._progress.get(run_id, RunProgressState()))
        except RunCancelledError:
            with self._lock:
                current_run = self._runs.get(run_id)
                progress = self._progress.get(run_id, RunProgressState())
            if current_run is None:
                current_run = _running_product_response(
                    product=product,
                    payload=payload,
                    run_id=run_id,
                    created_at=created_at,
                    artifact_dir=artifact_dir,
                    retry_of_run_id=retry_of_run_id,
                )
            run = _canceled_response(current_run, progress)
        except Exception as error:  # pragma: no cover - defensive path
            if cancel_event.is_set():
                with self._lock:
                    current_run = self._runs.get(run_id)
                    progress = self._progress.get(run_id, RunProgressState())
                run = _canceled_response(
                    current_run
                    or _running_product_response(
                        product=product,
                        payload=payload,
                        run_id=run_id,
                        created_at=created_at,
                        artifact_dir=artifact_dir,
                        retry_of_run_id=retry_of_run_id,
                    ),
                    progress,
                )
            else:
                run = _failed_response(
                    product=product,
                    payload=payload,
                    run_id=run_id,
                    created_at=created_at,
                    artifact_dir=artifact_dir,
                    error=error,
                    retry_of_run_id=retry_of_run_id,
                )
        self._set_run(run)
        state_store.save_run(run)

    def _register_run(
        self,
        run: GenerationRunResponse,
        context: ProductRunContext,
        cancel_event: Event,
    ) -> None:
        with self._lock:
            self._runs[run.run_id] = run
            self._contexts[run.run_id] = context
            self._cancel_events[run.run_id] = cancel_event

    def _set_run(self, run: GenerationRunResponse) -> None:
        with self._lock:
            self._runs[run.run_id] = run

    def _update_progress(
        self,
        run_id: str,
        generated_rows: int,
        current_resource: str,
        cancel_event: Event,
    ) -> None:
        _raise_if_canceled(cancel_event)
        with self._lock:
            self._progress[run_id] = RunProgressState(
                generated_rows=generated_rows,
                current_resource=current_resource,
                updated_at=datetime.now(UTC),
            )
        _raise_if_canceled(cancel_event)


def _running_product_response(
    *,
    product: ProductCatalogEntry,
    payload: ProductRunRequest,
    run_id: str,
    created_at: datetime,
    artifact_dir: Path,
    retry_of_run_id: str | None = None,
) -> GenerationRunResponse:
    source = _source_for_payload(product, payload)
    row_counts = payload.row_counts or _source_default_counts(source) or product.default_counts
    output_formats = tuple(payload.output_formats or product.output_formats)
    total_rows = sum(row_counts.values())
    match product.kind:
        case DataProductKind.RELATIONAL:
            tables = _planned_table_artifacts(product, payload, artifact_dir, output_formats)
            table_count = len(tables)
            collections = ()
        case DataProductKind.DOCUMENT:
            collections = _planned_collection_artifacts(
                product,
                row_counts,
                artifact_dir,
                output_formats,
                source=source,
            )
            table_count = len(collections)
            tables = ()
        case DataProductKind.GRAPH | DataProductKind.MASKING:
            raise ValueError(f"{product.name} is planned and is not runnable yet")

    return GenerationRunResponse(
        run_id=run_id,
        retry_of_run_id=retry_of_run_id,
        kind=product.kind,
        status=RunStatus.RUNNING,
        created_at=created_at,
        artifact_dir=artifact_dir,
        domain=product.domain,
        output_formats=output_formats,
        total_rows=total_rows,
        table_count=table_count,
        generated_rows=0,
        progress_percent=0.0,
        expected_seconds=_expected_seconds(total_rows),
        current_operation="export_artifacts",
        operation_timings=(
            OperationTimingResponse(
                operation="generate_async",
                status=OperationStatus.RUNNING,
                elapsed_seconds=0.0,
                started_at=created_at,
            ),
        ),
        tables=tables,
        collections=collections,
    )


def _planned_table_artifacts(
    product: ProductCatalogEntry,
    payload: ProductRunRequest,
    artifact_dir: Path,
    output_formats: tuple[str, ...],
) -> tuple[TableArtifactResponse, ...]:
    source = _source_for_payload(product, payload)
    schema_ddl = _schema_ddl_for_source(source) if source else product.schema_ddl
    if schema_ddl is None:
        raise ValueError("relational product is missing schema DDL")
    database = parse_postgres_ddl(schema_ddl)
    plan = create_generation_plan(
        database,
        row_counts=payload.row_counts or product.default_counts,
        seed=payload.seed,
        domain=product.domain,
        output_formats=tuple(OutputFormat(output_format) for output_format in output_formats),
    )
    return tuple(
        TableArtifactResponse(
            table_name=table.table_name,
            row_count=table.row_count,
            csv_path=artifact_dir / f"{_safe_filename(table.table_name)}.csv"
            if "csv" in output_formats
            else None,
            json_path=artifact_dir / f"{_safe_filename(table.table_name)}.json"
            if "json" in output_formats
            else None,
            sql_path=artifact_dir / f"{_safe_filename(table.table_name)}.sql"
            if "sql" in output_formats
            else None,
        )
        for table in plan.tables
    )


def _planned_collection_artifacts(
    product: ProductCatalogEntry,
    row_counts: dict[str, int],
    artifact_dir: Path,
    output_formats: tuple[str, ...],
    *,
    source: WorkspaceSource | None = None,
) -> tuple[CollectionArtifactResponse, ...]:
    collections = (
        _document_collections_for_source(source) if source else product.document_collections
    )
    return tuple(
        CollectionArtifactResponse(
            collection_name=collection.name,
            row_count=row_counts.get(collection.name, collection.default_count),
            json_path=artifact_dir / f"{collection.name}.json"
            if "json" in output_formats
            else None,
            ndjson_path=artifact_dir / f"{collection.name}.ndjson"
            if "ndjson" in output_formats
            else None,
        )
        for collection in collections
    )


def _failed_response(
    *,
    product: ProductCatalogEntry,
    payload: ProductRunRequest,
    run_id: str,
    created_at: datetime,
    artifact_dir: Path,
    error: Exception,
    retry_of_run_id: str | None = None,
) -> GenerationRunResponse:
    completed_at = datetime.now(UTC)
    source = _source_for_payload(product, payload)
    row_counts = payload.row_counts or _source_default_counts(source) or product.default_counts
    total_rows = sum(row_counts.values())
    return GenerationRunResponse(
        run_id=run_id,
        retry_of_run_id=retry_of_run_id,
        kind=product.kind,
        status=RunStatus.FAILED,
        created_at=created_at,
        completed_at=completed_at,
        artifact_dir=artifact_dir,
        domain=product.domain,
        output_formats=tuple(payload.output_formats or product.output_formats),
        total_rows=total_rows,
        table_count=len(source.resources) if source else len(product.tables or product.collections),
        generated_rows=0,
        progress_percent=100.0,
        current_operation="failed",
        operation_timings=(
            OperationTimingResponse(
                operation="generate_async",
                status=OperationStatus.FAILED,
                elapsed_seconds=round((completed_at - created_at).total_seconds(), 3),
                started_at=created_at,
                completed_at=completed_at,
            ),
        ),
        error=_format_error(error),
    )


def _canceled_response(
    run: GenerationRunResponse,
    progress: RunProgressState,
) -> GenerationRunResponse:
    completed_at = datetime.now(UTC)
    elapsed_seconds = max((completed_at - run.created_at).total_seconds(), 0.0)
    generated_rows = max(progress.generated_rows, run.generated_rows, 0)
    rows_per_second = _rows_per_second(generated_rows, elapsed_seconds)
    progress_percent = max(
        run.progress_percent,
        _row_progress_percent(generated_rows, run.total_rows),
    )
    return run.model_copy(
        update={
            "status": RunStatus.CANCELED,
            "completed_at": completed_at,
            "generated_rows": generated_rows,
            "progress_percent": round(progress_percent, 2),
            "remaining_seconds": None,
            "current_operation": "canceled",
            "current_resource": progress.current_resource,
            "rows_per_second": rows_per_second,
            "operation_timings": (
                OperationTimingResponse(
                    operation="generate_async",
                    status=OperationStatus.CANCELED,
                    elapsed_seconds=round(elapsed_seconds, 3),
                    started_at=run.created_at,
                    completed_at=completed_at,
                ),
            ),
            "error": "run canceled by user",
        }
    )


def _with_running_progress(
    run: GenerationRunResponse,
    progress: RunProgressState,
) -> GenerationRunResponse:
    elapsed_seconds = max((datetime.now(UTC) - run.created_at).total_seconds(), 0.0)
    expected_seconds = run.expected_seconds or _expected_seconds(run.total_rows)
    generated_rows = max(progress.generated_rows, 0)
    row_progress_percent = _row_progress_percent(generated_rows, run.total_rows)
    elapsed_progress_percent = min((elapsed_seconds / expected_seconds) * 5.0, 5.0)
    progress_percent = row_progress_percent if generated_rows else elapsed_progress_percent
    rows_per_second = _rows_per_second(generated_rows, elapsed_seconds)
    return run.model_copy(
        update={
            "generated_rows": generated_rows,
            "progress_percent": round(progress_percent, 2),
            "remaining_seconds": _remaining_seconds(
                total_rows=run.total_rows,
                generated_rows=generated_rows,
                rows_per_second=rows_per_second,
            ),
            "current_operation": "export_artifacts",
            "current_resource": progress.current_resource,
            "rows_per_second": rows_per_second,
            "operation_timings": (
                OperationTimingResponse(
                    operation="generate_async",
                    status=OperationStatus.RUNNING,
                    elapsed_seconds=round(elapsed_seconds, 3),
                    started_at=run.created_at,
                ),
            ),
        }
    )


def _expected_seconds(total_rows: int) -> float:
    return round(max(total_rows / BASELINE_RECORDS_PER_SECOND, 1.0), 3)


def _row_progress_percent(generated_rows: int, total_rows: int) -> float:
    if total_rows <= 0:
        return 95.0
    return min((generated_rows / total_rows) * 95.0, 95.0)


def _rows_per_second(generated_rows: int, elapsed_seconds: float) -> float | None:
    if generated_rows <= 0 or elapsed_seconds <= 0:
        return None
    return round(generated_rows / elapsed_seconds, 2)


def _remaining_seconds(
    *,
    total_rows: int,
    generated_rows: int,
    rows_per_second: float | None,
) -> float | None:
    if rows_per_second is None or rows_per_second <= 0:
        return None
    return round(max(total_rows - generated_rows, 0) / rows_per_second, 3)


def _raise_if_canceled(cancel_event: Event) -> None:
    if cancel_event.is_set():
        raise RunCancelledError


def _format_error(error: Exception) -> str:
    message = str(error).strip()
    if message:
        return f"{type(error).__name__}: {message}"
    return type(error).__name__


def _safe_filename(value: str) -> str:
    return value.replace(".", "__").replace("/", "_")
