from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

from databoom.synthesis import (
    AdapterAvailability,
    CandidateConfig,
    CandidateDecision,
    CandidateStatus,
    ColumnContract,
    ColumnKind,
    DataSensitivity,
    DatasetContract,
    EvaluationPolicy,
    SplitRequest,
    TournamentRequest,
)
from databoom.synthesis.adapters.base import AdapterRegistry
from databoom.synthesis.adapters.empirical import IndependentEmpiricalAdapter
from databoom.synthesis.contracts import DeterminismLevel, SynthesizerCapabilities
from databoom.synthesis.splitting import split_csv_dataset
from databoom.synthesis.tournament import run_tournament


def test_empirical_tournament_writes_evidence_but_never_approves_release(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.csv"
    _write_source(source)
    split = split_csv_dataset(
        SplitRequest(source_path=source, output_dir=tmp_path / "split", seed="split-seed")
    )
    dataset = DatasetContract(
        name="quality-fixture",
        columns=(
            ColumnContract(
                name="value",
                kind=ColumnKind.CONTINUOUS,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="segment",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )
    experiment = tmp_path / "experiment"
    report = run_tournament(
        TournamentRequest(
            split_manifest_path=tmp_path / "split" / "split-manifest.json",
            dataset_contract=dataset,
            experiment_root=experiment,
            candidates=(CandidateConfig(adapter_name="empirical-independent"),),
            sample_row_count=100,
            fit_seed="fit-seed",
            evaluation_seed="evaluation-seed",
            policy=EvaluationPolicy(
                maximum_numeric_ks=1.0,
                maximum_normalized_mean_error=100.0,
                maximum_categorical_tv=1.0,
                minimum_synthetic_uniqueness=0.0,
                maximum_exact_training_match_rate=1.0,
            ),
        )
    )

    assert split.training.row_count + split.validation.row_count + split.holdout.row_count == 400
    assert report.decision == CandidateDecision.RECOMMENDED_FOR_CONTROLLED_EVALUATION
    assert report.recommended_adapter == "empirical-independent"
    assert report.release_approved is False
    assert report.candidates[0].status == CandidateStatus.COMPLETED
    assert report.candidates[0].quality_report is not None
    assert report.candidates[0].quality_report.evidence_complete is False
    assert report.quality_intent_id == "default-tabular-v1"
    assert report.training_profile_manifest_path == "profiles/training/profile-manifest.json"
    assert report.holdout_profile_manifest_path == "profiles/holdout/profile-manifest.json"
    assert report.candidates[0].synthetic_profile_manifest_path == (
        "empirical-independent/synthetic-profile/profile-manifest.json"
    )
    assert (experiment / "tournament-report.json").is_file()
    assert (experiment / "empirical-independent" / "quality-report.json").is_file()
    assert (experiment / report.training_profile_manifest_path).is_file()
    assert (experiment / report.holdout_profile_manifest_path).is_file()
    assert (experiment / report.candidates[0].synthetic_profile_manifest_path).is_file()


def test_always_available_baselines_share_the_tournament_contract(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_source(source)
    split_csv_dataset(
        SplitRequest(source_path=source, output_dir=tmp_path / "split", seed="split-seed")
    )
    dataset = DatasetContract(
        name="base-candidates",
        columns=(
            ColumnContract(
                name="value",
                kind=ColumnKind.CONTINUOUS,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="segment",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )
    experiment = tmp_path / "experiment"
    report = run_tournament(
        TournamentRequest(
            split_manifest_path=tmp_path / "split" / "split-manifest.json",
            dataset_contract=dataset,
            experiment_root=experiment,
            candidates=(
                CandidateConfig(adapter_name="empirical-independent"),
                CandidateConfig(
                    adapter_name="gaussian-copula",
                    hyperparameters={"sample_size": 100, "regularization": 0.05},
                ),
            ),
            sample_row_count=50,
            fit_seed="fit",
            evaluation_seed="evaluation",
            policy=EvaluationPolicy(
                maximum_numeric_ks=1.0,
                maximum_normalized_mean_error=100.0,
                maximum_categorical_tv=1.0,
                minimum_synthetic_uniqueness=0.0,
                maximum_exact_training_match_rate=1.0,
            ),
        )
    )

    assert {candidate.adapter_name for candidate in report.candidates} == {
        "empirical-independent",
        "gaussian-copula",
    }
    assert all(candidate.status == CandidateStatus.COMPLETED for candidate in report.candidates)
    assert all(candidate.synthetic_profile_manifest_path for candidate in report.candidates)
    assert report.release_approved is False


def test_exact_copy_privacy_gate_overrides_fidelity(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("value", "segment"), lineterminator="\n")
        writer.writeheader()
        for index in range(120):
            writer.writerow({"value": index % 2, "segment": "same"})
    split_csv_dataset(
        SplitRequest(source_path=source, output_dir=tmp_path / "split", seed="split-seed")
    )
    dataset = DatasetContract(
        name="copy-fixture",
        columns=(
            ColumnContract(
                name="value",
                kind=ColumnKind.CONTINUOUS,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="segment",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )
    report = run_tournament(
        TournamentRequest(
            split_manifest_path=tmp_path / "split" / "split-manifest.json",
            dataset_contract=dataset,
            experiment_root=tmp_path / "experiment",
            candidates=(CandidateConfig(adapter_name="empirical-independent"),),
            sample_row_count=50,
            fit_seed="fit",
            evaluation_seed="evaluation",
            policy=EvaluationPolicy(
                maximum_numeric_ks=1.0,
                maximum_normalized_mean_error=100.0,
                maximum_categorical_tv=1.0,
                minimum_synthetic_uniqueness=0.0,
                maximum_exact_training_match_rate=0.0,
            ),
        )
    )

    assert report.decision == CandidateDecision.NOT_RECOMMENDED
    quality = report.candidates[0].quality_report
    assert quality is not None
    privacy_gate = next(gate for gate in quality.gates if gate.name == "exact_copy_privacy")
    assert privacy_gate.status.value == "failed"


def test_candidate_failure_does_not_discard_other_candidate_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_source(source)
    split_csv_dataset(
        SplitRequest(source_path=source, output_dir=tmp_path / "split", seed="split-seed")
    )
    dataset = DatasetContract(
        name="failure-isolation",
        columns=(
            ColumnContract(
                name="value",
                kind=ColumnKind.CONTINUOUS,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="segment",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )
    registry = AdapterRegistry()
    registry.register(_FailingAdapter())
    registry.register(IndependentEmpiricalAdapter())
    report = run_tournament(
        TournamentRequest(
            split_manifest_path=tmp_path / "split" / "split-manifest.json",
            dataset_contract=dataset,
            experiment_root=tmp_path / "experiment",
            candidates=(
                CandidateConfig(adapter_name="always-fails"),
                CandidateConfig(adapter_name="empirical-independent"),
            ),
            sample_row_count=50,
            fit_seed="fit",
            evaluation_seed="evaluation",
            policy=EvaluationPolicy(
                maximum_numeric_ks=1.0,
                maximum_normalized_mean_error=100.0,
                maximum_categorical_tv=1.0,
                minimum_synthetic_uniqueness=0.0,
                maximum_exact_training_match_rate=1.0,
            ),
        ),
        registry=registry,
    )

    statuses = {candidate.adapter_name: candidate.status for candidate in report.candidates}
    assert statuses == {
        "always-fails": CandidateStatus.FAILED,
        "empirical-independent": CandidateStatus.COMPLETED,
    }
    assert report.recommended_adapter == "empirical-independent"


def test_unknown_candidate_is_rejected_before_experiment_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_source(source)
    split_csv_dataset(
        SplitRequest(source_path=source, output_dir=tmp_path / "split", seed="split-seed")
    )
    dataset = DatasetContract(
        name="unknown-candidate",
        columns=(
            ColumnContract(
                name="value",
                kind=ColumnKind.CONTINUOUS,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="segment",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )
    experiment = tmp_path / "experiment"

    with pytest.raises(ValueError, match="unknown synthesizer adapters: missing-adapter"):
        run_tournament(
            TournamentRequest(
                split_manifest_path=tmp_path / "split" / "split-manifest.json",
                dataset_contract=dataset,
                experiment_root=experiment,
                candidates=(CandidateConfig(adapter_name="missing-adapter"),),
                sample_row_count=10,
                fit_seed="fit",
                evaluation_seed="evaluation",
            )
        )

    assert not experiment.exists()


@pytest.mark.skipif(
    any(
        importlib.util.find_spec(name) is None
        for name in ("ctgan", "numpy", "pandas", "sklearn", "tensorflow", "torch")
    ),
    reason="all optional synthesis extras are not installed",
)
def test_optional_candidates_share_one_tournament_contract(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_source(source)
    split_csv_dataset(
        SplitRequest(source_path=source, output_dir=tmp_path / "split", seed="split-seed")
    )
    dataset = DatasetContract(
        name="all-candidates",
        columns=(
            ColumnContract(
                name="value",
                kind=ColumnKind.CONTINUOUS,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="segment",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )
    report = run_tournament(
        TournamentRequest(
            split_manifest_path=tmp_path / "split" / "split-manifest.json",
            dataset_contract=dataset,
            experiment_root=tmp_path / "experiment",
            candidates=(
                CandidateConfig(adapter_name="empirical-independent"),
                CandidateConfig(
                    adapter_name="gaussian-copula",
                    hyperparameters={"sample_size": 100},
                ),
                CandidateConfig(
                    adapter_name="sklearn-gaussian-mixture",
                    hyperparameters={"n_components": 2},
                ),
                CandidateConfig(
                    adapter_name="tensorflow-gan",
                    hyperparameters={
                        "epochs": 1,
                        "batch_size": 16,
                        "latent_dim": 8,
                        "hidden_dim": 16,
                    },
                ),
                CandidateConfig(
                    adapter_name="ctgan",
                    hyperparameters={"epochs": 1, "batch_size": 20, "pac": 10},
                ),
            ),
            sample_row_count=20,
            fit_seed="fit",
            evaluation_seed="evaluation",
            policy=EvaluationPolicy(
                maximum_numeric_ks=1.0,
                maximum_normalized_mean_error=100.0,
                maximum_categorical_tv=1.0,
                minimum_synthetic_uniqueness=0.0,
                maximum_exact_training_match_rate=1.0,
            ),
        )
    )

    assert {candidate.adapter_name for candidate in report.candidates} == {
        "empirical-independent",
        "gaussian-copula",
        "sklearn-gaussian-mixture",
        "tensorflow-gan",
        "ctgan",
    }
    assert all(candidate.status == CandidateStatus.COMPLETED for candidate in report.candidates)
    assert all(candidate.sample_path for candidate in report.candidates)
    assert report.sample_row_count == 20
    assert report.release_approved is False


def _write_source(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("value", "segment"), lineterminator="\n")
        writer.writeheader()
        for index in range(400):
            writer.writerow(
                {
                    "value": index + (index % 7) / 10,
                    "segment": ("a", "b", "c", "d")[index % 4],
                }
            )


class _FailingAdapter:
    @property
    def capabilities(self) -> SynthesizerCapabilities:
        return SynthesizerCapabilities(
            name="always-fails",
            implementation_version="test",
            determinism=DeterminismLevel.DETERMINISTIC,
            complexity_tier=2,
            availability=AdapterAvailability.AVAILABLE,
        )

    def fit(self, *args, **kwargs):
        raise RuntimeError("controlled test failure")

    def sample(self, *args, **kwargs):
        raise AssertionError("sample must not run after failed fit")
