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

    COMPLETED = "completed"
    FAILED = "failed"


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


class GenerationRunResponse(BaseModel):
    """Generation run state returned by the API."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: RunStatus
    created_at: datetime
    completed_at: datetime | None = None
    artifact_dir: Path
    manifest_path: Path | None = None
    validation_path: Path | None = None
    domain: DomainProfile
    output_formats: tuple[OutputFormat, ...]
    total_rows: int
    table_count: int
    tables: tuple[TableArtifactResponse, ...] = ()
    validation: ValidationSummaryResponse | None = None
    error: str | None = None
