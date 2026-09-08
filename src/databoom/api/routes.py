"""HTTP routes for the DataBoom API.

Purpose:
    Expose health, auth, product catalog, workspace source, generation run,
    preview, and artifact download workflows.

Data flow:
    HTTP request -> Pydantic request model -> route validation -> service/helper
    modules -> Pydantic response model.

Why this layer exists:
    Routes should stay thin. They translate HTTP concerns into backend calls while
    engine decisions remain in `runs.py`, `generation/`, `profiling/`, and
    `validation/`.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import SQLAlchemyError

from databoom import __version__
from databoom.api.async_jobs import RunControlError, RunNotFoundError
from databoom.api.models import (
    CollectionArtifactResponse,
    DemoUserResponse,
    DocumentPreviewResponse,
    GenerationRunRequest,
    GenerationRunResponse,
    HealthResponse,
    LoginRequest,
    LoginResponse,
    ProductPlanResponse,
    ProductResponse,
    ProductRunRequest,
    RunArtifactListResponse,
    SubscriptionRequest,
    SubscriptionResponse,
    SubscriptionStatus,
    TableArtifactResponse,
    TablePreviewResponse,
    WorkspaceChildCountFrequencyResponse,
    WorkspaceColumnProfileResponse,
    WorkspaceColumnResponse,
    WorkspaceConnectionTestRequest,
    WorkspaceConnectionTestResponse,
    WorkspaceForeignKeyResponse,
    WorkspaceRelationshipProfileResponse,
    WorkspaceResourceResponse,
    WorkspaceSourceProfileRequest,
    WorkspaceSourceProfileResponse,
    WorkspaceSourceRefreshRequest,
    WorkspaceSourceRequest,
    WorkspaceSourceResponse,
    WorkspaceTableProfileResponse,
    WorkspaceTopValueResponse,
    WorkspaceUniqueConstraintResponse,
)
from databoom.api.products import ProductCatalogEntry, get_product, list_products
from databoom.api.runs import (
    execute_generation_run,
    execute_product_generation_run,
    list_generation_run_artifacts,
    resolve_generation_run_artifact,
)
from databoom.api.security import require_api_key
from databoom.api.state import StateStore
from databoom.api.workspaces import (
    WorkspaceSource,
    workspace_source_from_request,
    workspace_source_from_schema,
)
from databoom.core.config import Settings
from databoom.ingest.postgres import load_postgres_schema
from databoom.profiling import (
    ConnectionTest,
    SourceProfile,
    profile_postgres_source,
    test_postgres_connection,
)

router = APIRouter()
protected_route = Depends(require_api_key)
session_scheme = HTTPBearer(auto_error=False)
session_credentials = Depends(session_scheme)

DEMO_EMAIL = "demo"
DEMO_PASSWORD = "demo"
DEMO_TOKEN = "demo-session-token"


def _require_demo_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = session_credentials,
) -> DemoUserResponse:
    """Resolve the local demo session token into a user response."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing session token",
        )

    user = _state_store(request).get_session(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid session token",
        )
    return user


demo_user_dependency = Depends(_require_demo_user)


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


@router.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(request: Request, payload: LoginRequest) -> LoginResponse:
    """Authenticate the built-in demo user."""

    if payload.email != DEMO_EMAIL or payload.password != DEMO_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    user = DemoUserResponse(email=DEMO_EMAIL, name="Demo Operator")
    _state_store(request).save_session(DEMO_TOKEN, user)
    return LoginResponse(token=DEMO_TOKEN, user=user)


@router.get("/me", response_model=DemoUserResponse, tags=["auth"])
def me(user: DemoUserResponse = demo_user_dependency) -> DemoUserResponse:
    """Return the authenticated demo user."""

    return user


@router.get("/products", response_model=tuple[ProductResponse, ...], tags=["products"])
def products() -> tuple[ProductResponse, ...]:
    """Return runnable DataBoom products."""

    return tuple(_product_response(product) for product in list_products())


@router.get("/products/{product_id}", response_model=ProductResponse, tags=["products"])
def product_detail(product_id: str) -> ProductResponse:
    """Return one runnable DataBoom product."""

    try:
        product = get_product(product_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product not found",
        ) from error
    return _product_response(product)


@router.get(
    "/workspace-sources",
    response_model=tuple[WorkspaceSourceResponse, ...],
    tags=["workspaces"],
)
def workspace_sources(request: Request) -> tuple[WorkspaceSourceResponse, ...]:
    """Return all configured dashboard workspace sources."""

    return tuple(
        _workspace_source_response(source)
        for source in _state_store(request).list_workspace_sources()
    )


@router.post(
    "/workspace-sources",
    response_model=WorkspaceSourceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workspaces"],
)
def save_workspace_source(
    request: Request,
    payload: WorkspaceSourceRequest,
    user: DemoUserResponse = demo_user_dependency,
) -> WorkspaceSourceResponse:
    """Create or replace a dashboard workspace source."""

    product = _get_product_or_404(payload.product_id)
    if product.kind != payload.kind:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace source kind must match product kind",
        )
    source = workspace_source_from_request(payload)
    _state_store(request).save_workspace_source(source)
    return _workspace_source_response(source)


@router.post(
    "/workspace-sources/test-connection",
    response_model=WorkspaceConnectionTestResponse,
    tags=["workspaces"],
)
def test_workspace_connection(
    payload: WorkspaceConnectionTestRequest,
    user: DemoUserResponse = demo_user_dependency,
) -> WorkspaceConnectionTestResponse:
    """Test a live PostgreSQL connection before source refresh or creation."""

    try:
        result = test_postgres_connection(payload.database_url)
    except SQLAlchemyError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return _workspace_connection_test_response(result)


@router.get(
    "/workspace-sources/{source_id}",
    response_model=WorkspaceSourceResponse,
    tags=["workspaces"],
)
def workspace_source_detail(request: Request, source_id: str) -> WorkspaceSourceResponse:
    """Return one configured dashboard workspace source."""

    source = _state_store(request).get_workspace_source(source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="workspace source not found",
        )
    return _workspace_source_response(source)


@router.post(
    "/workspace-sources/{source_id}/refresh",
    response_model=WorkspaceSourceResponse,
    tags=["workspaces"],
)
def refresh_workspace_source(
    request: Request,
    source_id: str,
    payload: WorkspaceSourceRefreshRequest,
    user: DemoUserResponse = demo_user_dependency,
) -> WorkspaceSourceResponse:
    """Refresh one relational workspace source from live PostgreSQL metadata.

    Refresh updates schema/resource metadata only. Profiling is a separate endpoint
    because it reads table data and can be more expensive.
    """

    source = _state_store(request).get_workspace_source(source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="workspace source not found",
        )
    if source.kind != "relational" or source.engine.lower() != "postgresql":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="only PostgreSQL relational sources can be refreshed",
        )

    try:
        database = load_postgres_schema(
            payload.database_url,
            schema_names=payload.schema_names,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except SQLAlchemyError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    refreshed = workspace_source_from_schema(
        source,
        database,
        default_estimated_rows=payload.default_estimated_rows,
    )
    _state_store(request).save_workspace_source(refreshed)
    return _workspace_source_response(refreshed)


@router.post(
    "/workspace-sources/{source_id}/profile",
    response_model=WorkspaceSourceProfileResponse,
    tags=["workspaces"],
)
def profile_workspace_source(
    request: Request,
    source_id: str,
    payload: WorkspaceSourceProfileRequest,
    user: DemoUserResponse = demo_user_dependency,
) -> WorkspaceSourceProfileResponse:
    """Profile one relational workspace source from live PostgreSQL data.

    The resulting snapshot feeds relationship and column hints during later
    product runs.
    """

    source = _state_store(request).get_workspace_source(source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="workspace source not found",
        )
    if source.kind != "relational" or source.engine.lower() != "postgresql":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="only PostgreSQL relational sources can be profiled",
        )

    try:
        profile = profile_postgres_source(
            payload.database_url,
            source,
            top_values_limit=payload.top_values_limit,
        )
    except SQLAlchemyError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    _state_store(request).save_source_profile(profile)
    return _workspace_source_profile_response(profile)


@router.get(
    "/workspace-sources/{source_id}/profile",
    response_model=WorkspaceSourceProfileResponse,
    tags=["workspaces"],
)
def workspace_source_profile_snapshot(
    request: Request,
    source_id: str,
    user: DemoUserResponse = demo_user_dependency,
) -> WorkspaceSourceProfileResponse:
    """Return the latest persisted source profile snapshot."""

    store = _state_store(request)
    if store.get_workspace_source(source_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="workspace source not found",
        )

    profile = store.get_source_profile(source_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source profile snapshot not found",
        )
    return _workspace_source_profile_response(profile)


@router.get(
    "/products/{product_id}/workspace-sources",
    response_model=tuple[WorkspaceSourceResponse, ...],
    tags=["workspaces"],
)
def product_workspace_sources(
    request: Request,
    product_id: str,
) -> tuple[WorkspaceSourceResponse, ...]:
    """Return workspace sources compatible with one product."""

    _get_product_or_404(product_id)
    return tuple(
        _workspace_source_response(source)
        for source in _state_store(request).list_workspace_sources(product_id=product_id)
    )


@router.get(
    "/subscriptions",
    response_model=tuple[SubscriptionResponse, ...],
    tags=["subscriptions"],
)
def list_subscriptions(
    request: Request,
    user: DemoUserResponse = demo_user_dependency,
) -> tuple[SubscriptionResponse, ...]:
    """Return demo subscriptions for the authenticated user."""

    return _state_store(request).list_subscriptions(user.email)


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["subscriptions"],
)
def subscribe(
    request: Request,
    payload: SubscriptionRequest,
    user: DemoUserResponse = demo_user_dependency,
) -> SubscriptionResponse:
    """Subscribe the demo user to one DataBoom product."""

    try:
        product = get_product(payload.product_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product not found",
        ) from error

    if payload.plan_id not in {plan.id for plan in product.plans}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="plan not found")

    subscription = SubscriptionResponse(
        subscription_id=f"sub_{user.email}_{product.id}_{payload.plan_id}".replace("-", "_"),
        product_id=product.id,
        plan_id=payload.plan_id,
        status=SubscriptionStatus.ACTIVE,
        user_email=user.email,
        created_at=datetime.now(UTC),
    )
    _state_store(request).save_subscription(subscription)
    return subscription


@router.post(
    "/products/{product_id}/runs",
    response_model=GenerationRunResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["products"],
)
def create_product_run(
    request: Request,
    product_id: str,
    payload: ProductRunRequest,
    user: DemoUserResponse = demo_user_dependency,
) -> GenerationRunResponse:
    """Run the generator with a subscribed product's schema and defaults."""

    try:
        product = get_product(product_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product not found",
        ) from error

    if _state_store(request).get_subscription(user.email, product.id) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="subscribe to this product before generating data",
        )
    store = _state_store(request)
    source = _validate_source_for_product(request, payload.source_id, product)
    source_profile = store.get_source_profile(source.id) if source is not None else None

    try:
        run = execute_product_generation_run(
            product,
            payload,
            request.app.state.settings,
            source=source,
            source_profile=source_profile,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    store.save_run(run)
    return run


@router.post(
    "/products/{product_id}/runs/async",
    response_model=GenerationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["products"],
)
def create_async_product_run(
    request: Request,
    product_id: str,
    payload: ProductRunRequest,
    user: DemoUserResponse = demo_user_dependency,
) -> GenerationRunResponse:
    """Start a catalog-backed generation run in the background."""

    product = _get_product_or_404(product_id)
    store = _state_store(request)
    if store.get_subscription(user.email, product.id) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="subscribe to this product before generating data",
        )
    source = _validate_source_for_product(request, payload.source_id, product)

    try:
        return request.app.state.async_run_manager.submit_product_run(
            product=product,
            payload=payload,
            settings=request.app.state.settings,
            state_store=store,
            source=source,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


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

    _state_store(request).save_run(run)
    return run


@router.get(
    "/runs",
    response_model=tuple[GenerationRunResponse, ...],
    tags=["runs"],
    dependencies=[protected_route],
)
def list_runs(request: Request) -> tuple[GenerationRunResponse, ...]:
    """Return known generation runs for the current API process."""

    return _state_store(request).list_runs()


@router.get(
    "/runs/{run_id}",
    response_model=GenerationRunResponse,
    tags=["runs"],
    dependencies=[protected_route],
)
def get_run(request: Request, run_id: str) -> GenerationRunResponse:
    """Return one generation run by ID."""

    return _get_existing_run(request, run_id)


@router.post(
    "/runs/{run_id}/cancel",
    response_model=GenerationRunResponse,
    tags=["runs"],
    dependencies=[protected_route],
)
def cancel_run(request: Request, run_id: str) -> GenerationRunResponse:
    """Request cooperative cancellation for a running async run."""

    try:
        return request.app.state.async_run_manager.cancel_run(run_id, _state_store(request))
    except RunNotFoundError as error:
        if _state_store(request).get_run(run_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="run not found",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="run is not active in this API process",
        ) from error
    except RunControlError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post(
    "/runs/{run_id}/retry",
    response_model=GenerationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["runs"],
    dependencies=[protected_route],
)
def retry_run(request: Request, run_id: str) -> GenerationRunResponse:
    """Retry a failed or canceled async product run."""

    try:
        return request.app.state.async_run_manager.retry_run(
            run_id,
            settings=request.app.state.settings,
            state_store=_state_store(request),
        )
    except RunNotFoundError as error:
        if _state_store(request).get_run(run_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="run not found",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="run retry context is unavailable in this API process",
        ) from error
    except RunControlError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


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


@router.get(
    "/runs/{run_id}/preview",
    response_model=TablePreviewResponse,
    tags=["runs"],
    dependencies=[protected_route],
)
def preview_run_table(
    request: Request,
    run_id: str,
    table: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> TablePreviewResponse:
    """Return the first rows from a generated table's CSV artifact."""

    run = _get_existing_run(request, run_id)
    table_artifact = _find_table_artifact(run, table)
    if table_artifact.csv_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="table does not have a CSV artifact",
        )

    path = table_artifact.csv_path.resolve()
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CSV artifact not found")

    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = tuple(dict(row) for _, row in zip(range(limit), reader, strict=False))
        columns = tuple(reader.fieldnames or ())

    return TablePreviewResponse(
        run_id=run.run_id,
        table_name=table_artifact.table_name,
        columns=columns,
        rows=rows,
    )


@router.get(
    "/runs/{run_id}/document-preview",
    response_model=DocumentPreviewResponse,
    tags=["runs"],
    dependencies=[protected_route],
)
def preview_run_documents(
    request: Request,
    run_id: str,
    collection: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> DocumentPreviewResponse:
    """Return the first documents from a generated collection artifact."""

    run = _get_existing_run(request, run_id)
    collection_artifact = _find_collection_artifact(run, collection)
    if collection_artifact.json_path is None and collection_artifact.ndjson_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="collection does not have a previewable artifact",
        )

    documents = _read_document_preview(collection_artifact, limit)
    if documents is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="document artifact not found",
        )

    return DocumentPreviewResponse(
        run_id=run.run_id,
        collection_name=collection_artifact.collection_name,
        documents=documents,
    )


def _get_existing_run(request: Request, run_id: str) -> GenerationRunResponse:
    run = request.app.state.async_run_manager.get_run(run_id)
    if run is None:
        run = _state_store(request).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return run


def _get_product_or_404(product_id: str) -> ProductCatalogEntry:
    try:
        return get_product(product_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product not found",
        ) from error


def _validate_source_for_product(
    request: Request,
    source_id: str | None,
    product: ProductCatalogEntry,
) -> WorkspaceSource | None:
    if source_id is None:
        return None
    source = _state_store(request).get_workspace_source(source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace source not found",
        )
    if source.product_id != product.id or source.kind != product.kind:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace source is not compatible with this product",
        )
    return source


def _state_store(request: Request) -> StateStore:
    """Return the configured persistence boundary from app state."""

    return request.app.state.state_store


def _product_response(product: ProductCatalogEntry) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        family=product.family,
        module=product.module,
        kind=product.kind,
        status=product.status,
        description=product.description,
        domain=product.domain,
        default_row_counts=product.default_counts,
        output_formats=product.output_formats,
        tables=product.tables,
        collections=product.collections,
        use_cases=product.use_cases,
        features=product.features,
        plans=tuple(
            ProductPlanResponse(
                id=plan.id,
                name=plan.name,
                price=plan.price,
                description=plan.description,
            )
            for plan in product.plans
        ),
    )


def _workspace_source_response(source: WorkspaceSource) -> WorkspaceSourceResponse:
    return WorkspaceSourceResponse(
        id=source.id,
        product_id=source.product_id,
        kind=source.kind,
        name=source.name,
        engine=source.engine,
        host=source.host,
        description=source.description,
        status=source.status,
        schema_ddl=source.schema_ddl,
        refreshed_at=source.refreshed_at,
        resources=tuple(
            WorkspaceResourceResponse(
                name=resource.name,
                resource_type=resource.resource_type,
                estimated_rows=resource.estimated_rows,
                columns=resource.columns,
                schema_name=resource.schema_name,
                primary_key=resource.primary_key,
                foreign_keys=tuple(
                    WorkspaceForeignKeyResponse(
                        columns=foreign_key.columns,
                        referred_schema=foreign_key.referred_schema,
                        referred_table=foreign_key.referred_table,
                        referred_columns=foreign_key.referred_columns,
                        name=foreign_key.name,
                        on_delete=foreign_key.on_delete,
                        on_update=foreign_key.on_update,
                    )
                    for foreign_key in resource.foreign_keys
                ),
                unique_constraints=tuple(
                    WorkspaceUniqueConstraintResponse(
                        columns=unique_constraint.columns,
                        name=unique_constraint.name,
                    )
                    for unique_constraint in resource.unique_constraints
                ),
                column_details=tuple(
                    WorkspaceColumnResponse(
                        name=column.name,
                        data_type=column.data_type,
                        type_family=column.type_family,
                        nullable=column.nullable,
                        default=column.default,
                        is_primary_key=column.is_primary_key,
                        is_foreign_key=column.is_foreign_key,
                    )
                    for column in resource.column_details
                ),
            )
            for resource in source.resources
        ),
    )


def _workspace_source_profile_response(profile: SourceProfile) -> WorkspaceSourceProfileResponse:
    return WorkspaceSourceProfileResponse(
        source_id=profile.source_id,
        generated_at=profile.generated_at,
        total_rows=profile.total_rows,
        tables=tuple(
            WorkspaceTableProfileResponse(
                name=table.name,
                schema_name=table.schema_name,
                row_count=table.row_count,
                columns=tuple(
                    WorkspaceColumnProfileResponse(
                        name=column.name,
                        data_type=column.data_type,
                        row_count=column.row_count,
                        null_count=column.null_count,
                        null_rate=column.null_rate,
                        distinct_count=column.distinct_count,
                        min_value=column.min_value,
                        max_value=column.max_value,
                        top_values=tuple(
                            WorkspaceTopValueResponse(
                                value=value.value,
                                count=value.count,
                            )
                            for value in column.top_values
                        ),
                    )
                    for column in table.columns
                ),
            )
            for table in profile.tables
        ),
        relationships=tuple(
            WorkspaceRelationshipProfileResponse(
                child_table=relationship.child_table,
                child_schema=relationship.child_schema,
                child_columns=relationship.child_columns,
                parent_table=relationship.parent_table,
                parent_schema=relationship.parent_schema,
                parent_columns=relationship.parent_columns,
                parent_key_count=relationship.parent_key_count,
                child_row_count=relationship.child_row_count,
                distinct_parent_keys_referenced=(
                    relationship.distinct_parent_keys_referenced
                ),
                min_children_per_parent=relationship.min_children_per_parent,
                max_children_per_parent=relationship.max_children_per_parent,
                average_children_per_parent=relationship.average_children_per_parent,
                empty_parent_count=relationship.empty_parent_count,
                child_count_frequencies=tuple(
                    WorkspaceChildCountFrequencyResponse(
                        child_count=frequency.child_count,
                        parent_frequency=frequency.parent_frequency,
                    )
                    for frequency in relationship.child_count_frequencies
                ),
            )
            for relationship in profile.relationships
        ),
    )


def _workspace_connection_test_response(
    result: ConnectionTest,
) -> WorkspaceConnectionTestResponse:
    return WorkspaceConnectionTestResponse(
        ok=result.ok,
        message=result.message,
        checked_at=result.checked_at,
    )


def _find_collection_artifact(
    run: GenerationRunResponse,
    collection_name: str,
) -> CollectionArtifactResponse:
    for collection in run.collections:
        if collection.collection_name == collection_name:
            return collection
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collection not found")


def _find_table_artifact(
    run: GenerationRunResponse,
    table_name: str,
) -> TableArtifactResponse:
    for table in run.tables:
        short_name = table.table_name.rsplit(".", maxsplit=1)[-1]
        if table.table_name == table_name or short_name == table_name:
            return table
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="table not found")


def _read_document_preview(
    collection_artifact: CollectionArtifactResponse,
    limit: int,
) -> tuple[dict[str, object], ...] | None:
    if collection_artifact.json_path is not None:
        path = collection_artifact.json_path.resolve()
        if path.is_file():
            try:
                return tuple(json.loads(path.read_text(encoding="utf-8"))[:limit])
            except json.JSONDecodeError:
                pass

    if collection_artifact.ndjson_path is None:
        return None

    path = collection_artifact.ndjson_path.resolve()
    if not path.is_file():
        return None

    documents: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if len(documents) >= limit:
                break
            if not line.strip():
                continue
            try:
                document = json.loads(line)
            except json.JSONDecodeError:
                break
            if isinstance(document, dict):
                documents.append(document)
    return tuple(documents)
