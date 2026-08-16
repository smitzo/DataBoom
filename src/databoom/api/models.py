"""API response models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from databoom.generation import DomainProfile, OutputFormat


class HealthResponse(BaseModel):
    """Health payload returned by the API service."""

    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    version: str
    environment: str
    artifact_root: Path


class RunStatus(StrEnum):
    """Lifecycle state for a generation run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class OperationStatus(StrEnum):
    """Lifecycle state for one measured run operation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ProductStatus(StrEnum):
    """Availability state for a DataBoom product module."""

    ACTIVE = "active"
    PLANNED = "planned"


class DataProductKind(StrEnum):
    """Major DataBoom generation surface."""

    RELATIONAL = "relational"
    DOCUMENT = "document"
    GRAPH = "graph"
    MASKING = "masking"


class SubscriptionStatus(StrEnum):
    """Lifecycle state for a demo subscription."""

    ACTIVE = "active"


class WorkspaceSourceStatus(StrEnum):
    """Connection lifecycle for a demo workspace source."""

    CONNECTED = "connected"
    PLANNED = "planned"


class LoginRequest(BaseModel):
    """Demo login request."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class DemoUserResponse(BaseModel):
    """Authenticated demo user returned by the local API."""

    model_config = ConfigDict(extra="forbid")

    email: str
    name: str


class LoginResponse(BaseModel):
    """Demo login response."""

    model_config = ConfigDict(extra="forbid")

    token: str
    user: DemoUserResponse


class ProductPlanResponse(BaseModel):
    """Available subscription plan for one product."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    price: str
    description: str


class ProductResponse(BaseModel):
    """DataBoom product module exposed to the frontend."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    family: str
    module: str
    kind: DataProductKind
    status: ProductStatus
    description: str
    domain: DomainProfile
    default_row_counts: dict[str, int]
    output_formats: tuple[str, ...]
    tables: tuple[str, ...]
    collections: tuple[str, ...] = ()
    use_cases: tuple[str, ...] = ()
    features: tuple[str, ...]
    plans: tuple[ProductPlanResponse, ...]


class SubscriptionRequest(BaseModel):
    """Subscribe the demo user to a product module."""

    model_config = ConfigDict(extra="forbid")

    product_id: str
    plan_id: str = "starter"


class SubscriptionResponse(BaseModel):
    """Demo subscription state."""

    model_config = ConfigDict(extra="forbid")

    subscription_id: str
    product_id: str
    plan_id: str
    status: SubscriptionStatus
    user_email: str
    created_at: datetime


class WorkspaceResourceResponse(BaseModel):
    """One source resource exposed in the dashboard rail."""

    model_config = ConfigDict(extra="forbid")

    name: str
    resource_type: str
    estimated_rows: int
    columns: tuple[str, ...] = ()
    schema_name: str | None = None
    primary_key: tuple[str, ...] = ()
    foreign_keys: tuple[WorkspaceForeignKeyResponse, ...] = ()
    unique_constraints: tuple[WorkspaceUniqueConstraintResponse, ...] = ()
    column_details: tuple[WorkspaceColumnResponse, ...] = ()


class WorkspaceColumnResponse(BaseModel):
    """Column metadata discovered for one source resource."""

    model_config = ConfigDict(extra="forbid")

    name: str
    data_type: str
    type_family: str
    nullable: bool
    default: str | None = None
    is_primary_key: bool = False
    is_foreign_key: bool = False


class WorkspaceForeignKeyResponse(BaseModel):
    """Foreign-key metadata discovered for one source resource."""

    model_config = ConfigDict(extra="forbid")

    columns: tuple[str, ...]
    referred_schema: str
    referred_table: str
    referred_columns: tuple[str, ...]
    name: str | None = None
    on_delete: str | None = None
    on_update: str | None = None


class WorkspaceUniqueConstraintResponse(BaseModel):
    """Unique constraint metadata discovered for one source resource."""

    model_config = ConfigDict(extra="forbid")

    columns: tuple[str, ...]
    name: str | None = None


class WorkspaceSourceResponse(BaseModel):
    """Database or source connection available to a DataBoom product."""

    model_config = ConfigDict(extra="forbid")

    id: str
    product_id: str
    kind: DataProductKind
    name: str
    engine: str
    host: str
    description: str
    status: WorkspaceSourceStatus
    resources: tuple[WorkspaceResourceResponse, ...]
    schema_ddl: str | None = None
    refreshed_at: datetime | None = None


class WorkspaceResourceRequest(BaseModel):
    """Resource metadata accepted when creating or updating a workspace source."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    resource_type: str = Field(min_length=1)
    estimated_rows: int = Field(default=100, ge=0)
    columns: tuple[str, ...] = ()

    @field_validator("columns")
    @classmethod
    def reject_empty_columns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not column.strip() for column in value):
            raise ValueError("columns cannot be empty")
        return value


class WorkspaceSourceRequest(BaseModel):
    """Create or replace one dashboard workspace source."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    kind: DataProductKind
    name: str = Field(min_length=1)
    engine: str = Field(min_length=1)
    host: str = Field(min_length=1)
    description: str = ""
    status: WorkspaceSourceStatus = WorkspaceSourceStatus.CONNECTED
    resources: tuple[WorkspaceResourceRequest, ...] = ()


class WorkspaceSourceRefreshRequest(BaseModel):
    """Refresh a relational workspace source from a live PostgreSQL database."""

    model_config = ConfigDict(extra="forbid")

    database_url: str = Field(min_length=1)
    schema_names: tuple[str, ...] = ("public",)
    default_estimated_rows: int = Field(default=100, ge=0)

    @field_validator("schema_names")
    @classmethod
    def require_schema_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("at least one schema is required")
        if any(not schema_name.strip() for schema_name in value):
            raise ValueError("schema names cannot be empty")
        return value


class ProductRunRequest(BaseModel):
    """Generation request based on a subscribed product catalog entry."""

    model_config = ConfigDict(extra="forbid")

    row_counts: dict[str, int] = Field(default_factory=dict)
    seed: str = "dashboard-demo"
    output_formats: tuple[str, ...] | None = None
    source_id: str | None = None

    @field_validator("row_counts")
    @classmethod
    def validate_row_counts(cls, value: dict[str, int]) -> dict[str, int]:
        for table_name, row_count in value.items():
            if not table_name.strip():
                raise ValueError("row count table names cannot be empty")
            if row_count < 0:
                raise ValueError("row counts cannot be negative")
            if row_count > 10_000:
                raise ValueError("dashboard product runs are limited to 10,000 rows per table")
        return value

    @field_validator("output_formats")
    @classmethod
    def require_output_formats(
        cls,
        value: tuple[str, ...] | None,
    ) -> tuple[str, ...] | None:
        if value is not None and not value:
            raise ValueError("at least one output format is required")
        if value is not None and any(not item.strip() for item in value):
            raise ValueError("output formats cannot be empty")
        return value


class GenerationRunRequest(BaseModel):
    """Request to execute a relational generation run through the API."""

    model_config = ConfigDict(extra="forbid")

    schema_ddl: str = Field(min_length=1)
    row_counts: dict[str, int] = Field(default_factory=dict)
    default_row_count: int = Field(default=10, ge=0)
    seed: str = "0"
    domain: DomainProfile = DomainProfile.GENERAL
    output_formats: tuple[OutputFormat, ...] = (OutputFormat.CSV,)

    @field_validator("row_counts")
    @classmethod
    def validate_row_counts(cls, value: dict[str, int]) -> dict[str, int]:
        for table_name, row_count in value.items():
            if not table_name.strip():
                raise ValueError("row count table names cannot be empty")
            if row_count < 0:
                raise ValueError("row counts cannot be negative")
        return value

    @field_validator("output_formats")
    @classmethod
    def require_output_formats(cls, value: tuple[OutputFormat, ...]) -> tuple[OutputFormat, ...]:
        if not value:
            raise ValueError("at least one output format is required")
        return value


class TableArtifactResponse(BaseModel):
    """API representation of generated table artifacts."""

    model_config = ConfigDict(extra="forbid")

    table_name: str
    row_count: int
    csv_path: Path | None = None
    json_path: Path | None = None
    sql_path: Path | None = None


class CollectionArtifactResponse(BaseModel):
    """API representation of generated document collection artifacts."""

    model_config = ConfigDict(extra="forbid")

    collection_name: str
    row_count: int
    json_path: Path | None = None
    ndjson_path: Path | None = None


class ValidationIssueResponse(BaseModel):
    """API representation of one validation issue."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    table_name: str | None = None


class ValidationSummaryResponse(BaseModel):
    """API representation of a validation report."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    checked_tables: tuple[str, ...]
    issues: tuple[ValidationIssueResponse, ...]


class OperationTimingResponse(BaseModel):
    """Measured timing for one run operation."""

    model_config = ConfigDict(extra="forbid")

    operation: str
    status: OperationStatus
    elapsed_seconds: float
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RunArtifactResponse(BaseModel):
    """API representation of one downloadable run artifact."""

    model_config = ConfigDict(extra="forbid")

    name: str
    relative_path: str
    size_bytes: int
    media_type: str
    download_url: str


class RunArtifactListResponse(BaseModel):
    """API representation of the downloadable files for one run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    artifact_dir: Path
    files: tuple[RunArtifactResponse, ...]


class TablePreviewResponse(BaseModel):
    """Small table preview returned from a generated CSV artifact."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    table_name: str
    columns: tuple[str, ...]
    rows: tuple[dict[str, str], ...]


class DocumentPreviewResponse(BaseModel):
    """Small document collection preview returned from JSON/NDJSON artifacts."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    collection_name: str
    documents: tuple[dict[str, object], ...]


class GenerationRunResponse(BaseModel):
    """Generation run state returned by the API."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    retry_of_run_id: str | None = None
    kind: DataProductKind = DataProductKind.RELATIONAL
    status: RunStatus
    created_at: datetime
    completed_at: datetime | None = None
    artifact_dir: Path
    manifest_path: Path | None = None
    validation_path: Path | None = None
    domain: DomainProfile
    output_formats: tuple[str, ...]
    total_rows: int
    table_count: int
    generated_rows: int = Field(default=0, ge=0)
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    expected_seconds: float | None = None
    remaining_seconds: float | None = None
    current_operation: str | None = None
    current_resource: str | None = None
    rows_per_second: float | None = None
    operation_timings: tuple[OperationTimingResponse, ...] = ()
    tables: tuple[TableArtifactResponse, ...] = ()
    collections: tuple[CollectionArtifactResponse, ...] = ()
    validation: ValidationSummaryResponse | None = None
    error: str | None = None
