"""Validated contracts shared by every generation planner.

Purpose:
    Give deterministic logic and optional LLM providers one small, reviewable
    language for proposing a generation run.

Data flow:
    product/source metadata -> `PlannerRequest` -> planner -> `PlanDecision` ->
    immutable `PlanProposal` -> human review -> generation request.

Why this approach:
    A model is allowed to propose counts and strategies, but it cannot execute a
    run or invent an unvalidated payload. Pydantic rejects unknown fields and
    invalid counts before a proposal reaches the API or engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from databoom.generation.domains import LocaleProfile


class PlanningModel(BaseModel):
    """Strict immutable base for planner-domain values."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProductKind(StrEnum):
    """Generation surfaces supported by the planner contract."""

    RELATIONAL = "relational"
    DOCUMENT = "document"
    GRAPH = "graph"


class PlanResourceKind(StrEnum):
    """Resource shapes a planner can target."""

    TABLE = "table"
    COLLECTION = "collection"
    NODE = "node"
    EDGE = "edge"


class PlannerMode(StrEnum):
    """Planner implementation that produced a proposal."""

    DETERMINISTIC = "deterministic"
    OPENAI = "openai"


class PlanReviewStatus(StrEnum):
    """Human review state for a proposal."""

    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class PlanResourceInput(PlanningModel):
    """Normalized source or product resource visible to a planner."""

    name: str = Field(min_length=1, max_length=200)
    kind: PlanResourceKind
    default_count: int = Field(ge=0, le=1_000_000)
    attributes: tuple[str, ...] = ()
    source_resource: str | None = None
    target_resource: str | None = None

    @model_validator(mode="after")
    def validate_edge_endpoints(self) -> PlanResourceInput:
        """Require endpoint labels only for edge resources."""

        endpoints = (self.source_resource, self.target_resource)
        if self.kind == PlanResourceKind.EDGE and not all(endpoints):
            raise ValueError("edge resources require source_resource and target_resource")
        if self.kind != PlanResourceKind.EDGE and any(endpoints):
            raise ValueError("only edge resources can define endpoints")
        return self


class PlannerRequest(PlanningModel):
    """Provider-neutral request for a proposed generation plan."""

    product_id: str = Field(min_length=1, max_length=120)
    product_kind: ProductKind
    intent: str = Field(min_length=1, max_length=4_000)
    seed: str = Field(min_length=1, max_length=256)
    locale: LocaleProfile = LocaleProfile.EN_US
    output_formats: tuple[str, ...] = Field(min_length=1)
    resources: tuple[PlanResourceInput, ...] = Field(min_length=1)

    @field_validator("output_formats")
    @classmethod
    def normalize_formats(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(value.strip().lower() for value in values))
        if any(not value for value in normalized):
            raise ValueError("output formats cannot be empty")
        return normalized

    @model_validator(mode="after")
    def require_unique_resources(self) -> PlannerRequest:
        names = [resource.name for resource in self.resources]
        if len(names) != len(set(names)):
            raise ValueError("planner resource names must be unique")
        return self


class PlanResource(PlanningModel):
    """One reviewed execution target returned by a planner."""

    name: str = Field(min_length=1, max_length=200)
    kind: PlanResourceKind
    target_count: int = Field(ge=0, le=1_000_000)
    strategy: str = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=1_000)


class PlanDecision(PlanningModel):
    """Small structured output that deterministic or LLM planners may produce."""

    summary: str = Field(min_length=1, max_length=2_000)
    resources: tuple[PlanResource, ...] = Field(min_length=1)
    constraints: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_unique_known_resources(self) -> PlanDecision:
        names = [resource.name for resource in self.resources]
        if len(names) != len(set(names)):
            raise ValueError("planned resource names must be unique")
        return self


class PlannerTelemetry(PlanningModel):
    """Safe usage and cache metrics captured for one planning attempt."""

    mode: PlannerMode
    model: str | None = None
    prompt_pack_version: str
    schema_fingerprint: str
    prompt_cache_key: str
    input_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    cache_write_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    fallback_reason: str | None = Field(default=None, max_length=500)


class PlanProposal(PlanningModel):
    """Reviewable plan persisted before generation begins."""

    plan_id: str = Field(min_length=1, max_length=80)
    planner_version: str
    product_id: str
    product_kind: ProductKind
    intent: str
    seed: str
    locale: LocaleProfile = LocaleProfile.EN_US
    output_formats: tuple[str, ...]
    decision: PlanDecision
    telemetry: PlannerTelemetry
    review_status: PlanReviewStatus = PlanReviewStatus.DRAFT
    reviewed_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_review_metadata(self) -> PlanProposal:
        reviewed = self.review_status != PlanReviewStatus.DRAFT
        if reviewed != bool(self.reviewed_by and self.reviewed_at):
            raise ValueError("reviewed plans require reviewer and review timestamp")
        return self
