"""Immutable contracts for source-trained synthesis experiments.

These models are safe to import in API and planning processes. They contain no
imports from pandas, NumPy, torch, CTGAN, or another training implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

type JsonScalar = str | int | float | bool | None


class SynthesisModel(BaseModel):
    """Strict immutable base for synthesis-domain values."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ColumnKind(StrEnum):
    """Supported single-table feature families."""

    CONTINUOUS = "continuous"
    DISCRETE = "discrete"


class DataSensitivity(StrEnum):
    """Training eligibility marker for the first experimental worker."""

    RESTRICTED = "restricted"
    NON_SENSITIVE = "non_sensitive"


class SplitStrategy(StrEnum):
    """How split units are identified."""

    ROW_HASH = "row_hash"
    GROUP_HASH = "group_hash"


class AdapterAvailability(StrEnum):
    """Whether a provider can run in the active worker environment."""

    AVAILABLE = "available"
    MISSING_DEPENDENCY = "missing_dependency"
    BLOCKED_BY_POLICY = "blocked_by_policy"


class DeterminismLevel(StrEnum):
    """Reproducibility guarantee declared by an adapter."""

    DETERMINISTIC = "deterministic"
    BEST_EFFORT = "best_effort"


class CandidateStatus(StrEnum):
    """Terminal execution status for one tournament candidate."""

    COMPLETED = "completed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class GateStatus(StrEnum):
    """Outcome for an independent quality or safety gate."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_EVALUATED = "not_evaluated"


class CandidateDecision(StrEnum):
    """Experimental recommendation outcome."""

    RECOMMENDED_FOR_CONTROLLED_EVALUATION = "recommended_for_controlled_evaluation"
    NOT_RECOMMENDED = "not_recommended"
    NO_ELIGIBLE_CANDIDATE = "no_eligible_candidate"


class ColumnContract(SynthesisModel):
    """One explicitly reviewed feature supplied to a synthesizer."""

    name: str = Field(min_length=1, max_length=200)
    kind: ColumnKind
    nullable: bool = False
    sensitivity: DataSensitivity = DataSensitivity.RESTRICTED


class DatasetContract(SynthesisModel):
    """Reviewed single-table training contract."""

    contract_version: str = "1"
    name: str = Field(min_length=1, max_length=200)
    columns: tuple[ColumnContract, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_columns(self) -> DatasetContract:
        names = [column.name for column in self.columns]
        if len(names) != len(set(names)):
            raise ValueError("dataset column names must be unique")
        return self

    @property
    def column_names(self) -> tuple[str, ...]:
        """Return columns in the reviewed output order."""

        return tuple(column.name for column in self.columns)

    @property
    def discrete_columns(self) -> tuple[str, ...]:
        """Return discrete feature names for provider preprocessing."""

        return tuple(column.name for column in self.columns if column.kind == ColumnKind.DISCRETE)

    def require_training_eligible(self) -> None:
        """Reject restricted features until privacy controls are implemented."""

        restricted = [
            column.name
            for column in self.columns
            if column.sensitivity == DataSensitivity.RESTRICTED
        ]
        if restricted:
            names = ", ".join(restricted)
            raise ValueError(f"restricted columns are not training-eligible: {names}")


class SplitRatios(SynthesisModel):
    """Train, validation, and holdout proportions."""

    training: float = Field(default=0.70, gt=0, lt=1)
    validation: float = Field(default=0.15, gt=0, lt=1)
    holdout: float = Field(default=0.15, gt=0, lt=1)

    @model_validator(mode="after")
    def require_unit_sum(self) -> SplitRatios:
        if abs(self.training + self.validation + self.holdout - 1.0) > 1e-9:
            raise ValueError("split ratios must sum to 1.0")
        return self


class SplitRequest(SynthesisModel):
    """Request for a deterministic local CSV split."""

    source_path: Path
    output_dir: Path
    seed: str = Field(min_length=1, max_length=256)
    ratios: SplitRatios = Field(default_factory=SplitRatios)
    group_columns: tuple[str, ...] = ()
    algorithm_version: str = "hash-v1"
    overwrite: bool = False

    @field_validator("group_columns")
    @classmethod
    def normalize_group_columns(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("group column names cannot be empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("group column names must be unique")
        return normalized

    @property
    def strategy(self) -> SplitStrategy:
        """Return the effective split strategy."""

        if self.group_columns:
            return SplitStrategy.GROUP_HASH
        return SplitStrategy.ROW_HASH


class PartitionArtifact(SynthesisModel):
    """One checksummed CSV partition."""

    name: str
    path: str
    row_count: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SplitManifest(SynthesisModel):
    """Reproducible evidence for one source partitioning operation."""

    manifest_version: str = "1"
    split_id: str = Field(min_length=1, max_length=80)
    source_name: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_row_count: int = Field(ge=3)
    columns: tuple[str, ...] = Field(min_length=1)
    algorithm_version: str
    strategy: SplitStrategy
    seed: str
    ratios: SplitRatios
    group_columns: tuple[str, ...] = ()
    training: PartitionArtifact
    validation: PartitionArtifact
    holdout: PartitionArtifact
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_partition_counts(self) -> SplitManifest:
        partitions = (self.training, self.validation, self.holdout)
        if any(partition.row_count <= 0 for partition in partitions):
            raise ValueError("training, validation, and holdout must all contain rows")
        if sum(partition.row_count for partition in partitions) != self.source_row_count:
            raise ValueError("partition row counts must equal source row count")
        return self


class SynthesizerCapabilities(SynthesisModel):
    """Machine-readable provider capability and availability declaration."""

    name: str
    implementation_version: str
    data_shapes: tuple[str, ...] = ("single_table",)
    supports_conditions: bool = False
    supports_missing_values: bool = False
    determinism: DeterminismLevel
    requires_gpu: bool = False
    complexity_tier: int = Field(ge=0)
    availability: AdapterAvailability
    dependency: str | None = None
    dependency_version: str | None = None
    dependency_license: str | None = None
    unavailable_reason: str | None = None


class FitConfig(SynthesisModel):
    """Provider-neutral fit settings."""

    seed: str = Field(min_length=1, max_length=256)
    hyperparameters: dict[str, JsonScalar] = Field(default_factory=dict)


class ModelManifest(SynthesisModel):
    """Checksummed lineage for one fitted synthesizer artifact."""

    manifest_version: str = "1"
    model_id: str = Field(min_length=1, max_length=100)
    adapter_name: str
    adapter_version: str
    dependency_versions: dict[str, str] = Field(default_factory=dict)
    dependency_license: str | None = None
    training_partition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_contract: DatasetContract
    hyperparameters: dict[str, JsonScalar] = Field(default_factory=dict)
    seed: str
    fit_seconds: float = Field(ge=0)
    artifact_format: str
    artifact_path: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    transform_metadata: dict[str, dict[str, JsonScalar]] = Field(default_factory=dict)
    trusted_local_only: bool = True
    warnings: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SampleArtifact(SynthesisModel):
    """Checksummed sampled CSV and runtime evidence."""

    path: str
    row_count: int = Field(gt=0)
    seed: str
    sample_seconds: float = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class MetricResult(SynthesisModel):
    """One independently reportable metric."""

    name: str
    dimension: str
    value: float | int | bool | None
    status: GateStatus
    threshold: float | int | bool | None = None
    column: str | None = None
    detail: str = ""


class GateResult(SynthesisModel):
    """One hard gate built from one or more metrics."""

    name: str
    status: GateStatus
    metric_names: tuple[str, ...] = ()
    detail: str = ""


class EvaluationPolicy(SynthesisModel):
    """Versioned experimental thresholds; not a production release policy."""

    policy_id: str = "experimental-tabular-v1"
    maximum_numeric_ks: float = Field(default=0.25, ge=0, le=1)
    maximum_normalized_mean_error: float = Field(default=0.50, ge=0)
    maximum_categorical_tv: float = Field(default=0.25, ge=0, le=1)
    minimum_synthetic_uniqueness: float = Field(default=0.80, ge=0, le=1)
    maximum_exact_training_match_rate: float = Field(default=0.0, ge=0, le=1)
    require_reproducible_sample: bool = True


class CandidateConfig(SynthesisModel):
    """One adapter and bounded hyperparameter configuration."""

    adapter_name: str = Field(min_length=1, max_length=100)
    hyperparameters: dict[str, JsonScalar] = Field(default_factory=dict)


class TournamentRequest(SynthesisModel):
    """Request for a local, experimental single-table candidate tournament."""

    split_manifest_path: Path
    dataset_contract: DatasetContract
    experiment_root: Path
    candidates: tuple[CandidateConfig, ...] = Field(min_length=1)
    sample_row_count: int = Field(gt=0, le=1_000_000)
    fit_seed: str = Field(min_length=1, max_length=256)
    evaluation_seed: str = Field(min_length=1, max_length=256)
    policy: EvaluationPolicy = Field(default_factory=EvaluationPolicy)
    overwrite: bool = False

    @model_validator(mode="after")
    def require_unique_candidates(self) -> TournamentRequest:
        names = [candidate.adapter_name for candidate in self.candidates]
        if len(names) != len(set(names)):
            raise ValueError("candidate adapter names must be unique")
        return self


class QualityReport(SynthesisModel):
    """Multidimensional experimental evidence for one candidate sample."""

    report_version: str = "1"
    adapter_name: str
    policy_id: str
    metrics: tuple[MetricResult, ...]
    gates: tuple[GateResult, ...]
    evidence_complete: bool = False
    release_approved: bool = False
    warnings: tuple[str, ...] = ()

    @property
    def hard_gates_passed(self) -> bool:
        """Return true only when every implemented hard gate passes."""

        return bool(self.gates) and all(gate.status == GateStatus.PASSED for gate in self.gates)


class CandidateResult(SynthesisModel):
    """Terminal result for one adapter within a tournament."""

    adapter_name: str
    status: CandidateStatus
    capabilities: SynthesizerCapabilities
    model_manifest_path: str | None = None
    sample_path: str | None = None
    quality_report_path: str | None = None
    quality_report: QualityReport | None = None
    error_type: str | None = None
    error_message: str | None = None


class TournamentReport(SynthesisModel):
    """Machine-readable comparison and experimental recommendation."""

    report_version: str = "1"
    experiment_id: str
    split_id: str
    sample_row_count: int = Field(gt=0)
    evaluation_seed: str
    candidates: tuple[CandidateResult, ...]
    decision: CandidateDecision
    recommended_adapter: str | None = None
    release_approved: bool = False
    missing_production_evidence: tuple[str, ...] = (
        "downstream utility",
        "membership and attribute inference",
        "signed model lineage",
        "isolated production worker",
        "calibrated release thresholds",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
