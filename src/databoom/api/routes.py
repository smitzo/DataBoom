"""HTTP routes for the DataBoom API."""

from __future__ import annotations

import csv
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from databoom import __version__
from databoom.api.models import (
    DemoUserResponse,
    GenerationRunRequest,
    GenerationRunResponse,
    HealthResponse,
    LoginRequest,
    LoginResponse,
    ProductPlanResponse,
    ProductResponse,
    ProductRunRequest,
    ProductStatus,
    RunArtifactListResponse,
    SubscriptionRequest,
    SubscriptionResponse,
    SubscriptionStatus,
    TableArtifactResponse,
    TablePreviewResponse,
)
from databoom.api.products import ProductCatalogEntry, get_product, list_products
from databoom.api.runs import (
    execute_generation_run,
    list_generation_run_artifacts,
    resolve_generation_run_artifact,
)
from databoom.api.security import require_api_key
from databoom.api.state import StateStore
from databoom.core.config import Settings

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

    settings: Settings = request.app.state.settings
    try:
        run = execute_generation_run(
            GenerationRunRequest(
                schema_ddl=product.schema_ddl,
                row_counts=payload.row_counts or product.default_row_counts,
                seed=payload.seed,
                domain=product.domain,
                output_formats=payload.output_formats or product.output_formats,
            ),
            settings,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    _state_store(request).save_run(run)
    return run


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


def _get_existing_run(request: Request, run_id: str) -> GenerationRunResponse:
    run = _state_store(request).get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return run


def _state_store(request: Request) -> StateStore:
    return request.app.state.state_store


def _product_response(product: ProductCatalogEntry) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        family=product.family,
        module=product.module,
        status=ProductStatus.ACTIVE,
        description=product.description,
        domain=product.domain,
        default_row_counts=product.default_row_counts,
        output_formats=product.output_formats,
        tables=product.tables,
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


def _find_table_artifact(
    run: GenerationRunResponse,
    table_name: str,
) -> TableArtifactResponse:
    for table in run.tables:
        short_name = table.table_name.rsplit(".", maxsplit=1)[-1]
        if table.table_name == table_name or short_name == table_name:
            return table
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="table not found")
