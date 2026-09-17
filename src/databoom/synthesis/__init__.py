"""Provider-neutral statistical and neural synthesis boundaries.

The package root intentionally imports only web-safe contracts. Training
libraries are loaded lazily inside adapter worker methods.
"""

from databoom.synthesis.contracts import (
    AdapterAvailability,
    CandidateConfig,
    CandidateDecision,
    CandidateResult,
    CandidateStatus,
    ColumnContract,
    ColumnKind,
    DataSensitivity,
    DatasetContract,
    EvaluationPolicy,
    GateResult,
    GateStatus,
    ModelManifest,
    PartitionArtifact,
    QualityReport,
    SampleArtifact,
    SplitManifest,
    SplitRatios,
    SplitRequest,
    SplitStrategy,
    SynthesizerCapabilities,
    TournamentReport,
    TournamentRequest,
)

__all__ = [
    "AdapterAvailability",
    "CandidateDecision",
    "CandidateConfig",
    "CandidateResult",
    "CandidateStatus",
    "ColumnContract",
    "ColumnKind",
    "DataSensitivity",
    "DatasetContract",
    "EvaluationPolicy",
    "GateResult",
    "GateStatus",
    "ModelManifest",
    "PartitionArtifact",
    "QualityReport",
    "SampleArtifact",
    "SplitManifest",
    "SplitRatios",
    "SplitRequest",
    "SplitStrategy",
    "SynthesizerCapabilities",
    "TournamentReport",
    "TournamentRequest",
]
