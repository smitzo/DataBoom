from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

from databoom.synthesis import (
    AdapterAvailability,
    ColumnContract,
    ColumnKind,
    DataSensitivity,
    DatasetContract,
)
from databoom.synthesis.adapters.base import SynthesizerUnavailableError
from databoom.synthesis.adapters.ctgan import CtganAdapter
from databoom.synthesis.adapters.empirical import IndependentEmpiricalAdapter
from databoom.synthesis.adapters.gaussian_copula import GaussianCopulaAdapter
from databoom.synthesis.adapters.sklearn_gmm import SklearnGaussianMixtureAdapter
from databoom.synthesis.adapters.tensorflow_gan import TensorflowGanAdapter
from databoom.synthesis.contracts import FitConfig
from databoom.synthesis.io import sha256_file


def test_empirical_adapter_is_deterministic_and_checks_model_integrity(tmp_path: Path) -> None:
    training = tmp_path / "training.csv"
    _write_training(training)
    dataset = _dataset_contract()
    adapter = IndependentEmpiricalAdapter()
    experiment = tmp_path / "experiment"

    manifest = adapter.fit(
        training,
        dataset,
        experiment,
        experiment / "model",
        FitConfig(seed="fit-seed", hyperparameters={"reservoir_size": 25}),
    )
    first = adapter.sample(
        manifest,
        experiment,
        experiment / "first.csv",
        row_count=50,
        seed="sample-seed",
    )
    second = adapter.sample(
        manifest,
        experiment,
        experiment / "second.csv",
        row_count=50,
        seed="sample-seed",
    )

    assert first.sha256 == second.sha256
    with (experiment / "first.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 50
    assert tuple(rows[0]) == dataset.column_names
    assert manifest.training_partition_sha256
    assert manifest.trusted_local_only is True

    model_path = experiment / manifest.artifact_path
    model_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        adapter.sample(
            manifest,
            experiment,
            experiment / "tampered.csv",
            row_count=5,
            seed="sample-seed",
        )

    escaped_manifest = manifest.model_copy(
        update={
            "artifact_path": "../training.csv",
            "artifact_sha256": sha256_file(training),
        }
    )
    with pytest.raises(ValueError, match="escapes the experiment root"):
        adapter.sample(
            escaped_manifest,
            experiment,
            experiment / "escaped.csv",
            row_count=5,
            seed="sample-seed",
        )


def test_training_rejects_restricted_columns(tmp_path: Path) -> None:
    training = tmp_path / "training.csv"
    _write_training(training)
    restricted = DatasetContract(
        name="restricted",
        columns=(
            ColumnContract(name="age", kind=ColumnKind.CONTINUOUS),
            ColumnContract(
                name="segment",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )

    with pytest.raises(ValueError, match="restricted columns"):
        IndependentEmpiricalAdapter().fit(
            training,
            restricted,
            tmp_path / "experiment",
            tmp_path / "experiment" / "model",
            FitConfig(seed="0"),
        )


def test_gaussian_copula_is_bounded_deterministic_and_restores_nullable_rows(
    tmp_path: Path,
) -> None:
    training = tmp_path / "training.csv"
    _write_training(training)
    dataset = _dataset_contract()
    adapter = GaussianCopulaAdapter()
    experiment = tmp_path / "experiment"

    manifest = adapter.fit(
        training,
        dataset,
        experiment,
        experiment / "model",
        FitConfig(
            seed="copula-fit",
            hyperparameters={"sample_size": 25, "regularization": 0.05},
        ),
    )
    first = adapter.sample(
        manifest,
        experiment,
        experiment / "first.csv",
        row_count=200,
        seed="copula-sample",
    )
    second = adapter.sample(
        manifest,
        experiment,
        experiment / "second.csv",
        row_count=200,
        seed="copula-sample",
    )

    assert first.sha256 == second.sha256
    assert manifest.artifact_format == "json"
    assert manifest.dependency_license == "PSF-2.0"
    assert manifest.transform_metadata["age"]["missingness_index"] == 1
    assert any("nominal categories" in warning for warning in manifest.warnings)
    payload = json.loads((experiment / manifest.artifact_path).read_text(encoding="utf-8"))
    assert payload["training_row_count"] == 100
    assert payload["retained_row_count"] == 25
    assert all(len(settings["values"]) <= 25 for settings in payload["columns"].values())
    with (experiment / "first.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 200
    assert tuple(rows[0]) == dataset.column_names
    assert all(row["age"] == "" or math.isfinite(float(row["age"])) for row in rows)
    assert {row["segment"] for row in rows} <= {"standard", "premium", "business"}


def test_gaussian_copula_preserves_strong_numeric_rank_dependence(tmp_path: Path) -> None:
    training = tmp_path / "correlated.csv"
    with training.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("x", "y"), lineterminator="\n")
        writer.writeheader()
        for index in range(500):
            writer.writerow({"x": index, "y": 3 * index + index % 5})
    dataset = DatasetContract(
        name="correlated",
        columns=(
            ColumnContract(
                name="x",
                kind=ColumnKind.CONTINUOUS,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="y",
                kind=ColumnKind.CONTINUOUS,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )
    experiment = tmp_path / "experiment"
    adapter = GaussianCopulaAdapter()
    manifest = adapter.fit(
        training,
        dataset,
        experiment,
        experiment / "model",
        FitConfig(
            seed="dependence-fit",
            hyperparameters={"sample_size": 500, "regularization": 0.02},
        ),
    )
    adapter.sample(
        manifest,
        experiment,
        experiment / "sample.csv",
        row_count=1_000,
        seed="dependence-sample",
    )
    with (experiment / "sample.csv").open("r", encoding="utf-8", newline="") as handle:
        pairs = [(float(row["x"]), float(row["y"])) for row in csv.DictReader(handle)]

    assert _pearson(pairs) > 0.9


def test_gaussian_copula_rejects_tampering_escape_and_invalid_matrix(tmp_path: Path) -> None:
    training = tmp_path / "training.csv"
    _write_training(training)
    dataset = _dataset_contract()
    adapter = GaussianCopulaAdapter()
    experiment = tmp_path / "experiment"
    manifest = adapter.fit(
        training,
        dataset,
        experiment,
        experiment / "model",
        FitConfig(seed="copula-fit", hyperparameters={"sample_size": 25}),
    )
    model_path = experiment / manifest.artifact_path
    original = model_path.read_text(encoding="utf-8")
    model_path.write_text("not JSON", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        adapter.sample(
            manifest,
            experiment,
            experiment / "tampered.csv",
            row_count=5,
            seed="sample",
        )

    escaped = manifest.model_copy(
        update={"artifact_path": "../training.csv", "artifact_sha256": sha256_file(training)}
    )
    with pytest.raises(ValueError, match="escapes the experiment root"):
        adapter.sample(
            escaped,
            experiment,
            experiment / "escaped.csv",
            row_count=5,
            seed="sample",
        )

    model_path.write_text(original, encoding="utf-8")
    payload = json.loads(original)
    payload["cholesky"] = [[1.0]]
    model_path.write_text(json.dumps(payload), encoding="utf-8")
    invalid = manifest.model_copy(update={"artifact_sha256": sha256_file(model_path)})
    with pytest.raises(ValueError, match="wrong dimensions"):
        adapter.sample(
            invalid,
            experiment,
            experiment / "invalid.csv",
            row_count=5,
            seed="sample",
        )


@pytest.mark.parametrize(
    ("hyperparameters", "message"),
    (
        ({"sample_size": True}, "sample_size must be an integer"),
        ({"sample_size": 9}, "sample_size must be between"),
        ({"regularization": float("nan")}, "finite number"),
        ({"regularization": 0.0}, "greater than 0"),
        ({"unknown": 1}, "unsupported Gaussian-copula"),
    ),
)
def test_gaussian_copula_rejects_invalid_hyperparameters_before_writing(
    tmp_path: Path,
    hyperparameters: dict[str, object],
    message: str,
) -> None:
    training = tmp_path / "training.csv"
    _write_training(training)
    experiment = tmp_path / "experiment"

    with pytest.raises(ValueError, match=message):
        GaussianCopulaAdapter().fit(
            training,
            _dataset_contract(),
            experiment,
            experiment / "model",
            FitConfig(seed="fit", hyperparameters=hyperparameters),
        )

    assert not experiment.exists()


def test_ctgan_is_lazy_and_missing_dependency_does_not_break_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_find_spec = importlib.util.find_spec

    def missing_ctgan(name: str, package: str | None = None):
        if name == "ctgan":
            return None
        return real_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", missing_ctgan)
    adapter = CtganAdapter()
    assert adapter.capabilities.availability == AdapterAvailability.MISSING_DEPENDENCY
    assert "torch" not in sys.modules
    assert "ctgan" not in sys.modules
    assert "sklearn" not in sys.modules
    assert "tensorflow" not in sys.modules

    from databoom.api.app import create_app

    assert create_app().title == "DataBoom API"
    assert "torch" not in sys.modules
    assert "ctgan" not in sys.modules
    assert "sklearn" not in sys.modules
    assert "tensorflow" not in sys.modules

    with pytest.raises(SynthesizerUnavailableError):
        adapter.fit(
            Path("missing.csv"),
            _dataset_contract(),
            Path("experiment"),
            Path("experiment/model"),
            FitConfig(seed="0"),
        )


@pytest.mark.parametrize(
    ("missing_name", "adapter_type", "module_name"),
    (
        ("sklearn", SklearnGaussianMixtureAdapter, "sklearn"),
        ("tensorflow", TensorflowGanAdapter, "tensorflow"),
    ),
)
def test_optional_ml_adapters_are_lazy_and_report_missing_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    missing_name: str,
    adapter_type,
    module_name: str,
) -> None:
    real_find_spec = importlib.util.find_spec

    def missing_provider(name: str, package: str | None = None):
        if name == missing_name:
            return None
        return real_find_spec(name, package)

    monkeypatch.setattr(importlib.util, "find_spec", missing_provider)
    adapter = adapter_type()

    assert adapter.capabilities.availability == AdapterAvailability.MISSING_DEPENDENCY
    assert module_name not in sys.modules
    with pytest.raises(SynthesizerUnavailableError):
        adapter.fit(
            Path("missing.csv"),
            _dataset_contract(),
            Path("experiment"),
            Path("experiment/model"),
            FitConfig(seed="0"),
        )


@pytest.mark.skipif(
    importlib.util.find_spec("numpy") is None or importlib.util.find_spec("sklearn") is None,
    reason="ml-sklearn extra is not installed",
)
def test_sklearn_gaussian_mixture_fit_sample_and_json_artifact(tmp_path: Path) -> None:
    training = tmp_path / "training.csv"
    _write_training(training)
    dataset = _dataset_contract()
    adapter = SklearnGaussianMixtureAdapter()
    experiment = tmp_path / "experiment"

    manifest = adapter.fit(
        training,
        dataset,
        experiment,
        experiment / "model",
        FitConfig(seed="gmm-fit", hyperparameters={"n_components": 3}),
    )
    first = adapter.sample(
        manifest,
        experiment,
        experiment / "first.csv",
        row_count=40,
        seed="gmm-sample",
    )
    second = adapter.sample(
        manifest,
        experiment,
        experiment / "second.csv",
        row_count=40,
        seed="gmm-sample",
    )

    assert manifest.artifact_format == "json"
    assert manifest.dependency_license == "BSD-3-Clause"
    assert first.sha256 == second.sha256
    with (experiment / "first.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 40
    assert tuple(rows[0]) == dataset.column_names


@pytest.mark.skipif(
    any(
        importlib.util.find_spec(name) is None
        for name in ("ctgan", "numpy", "pandas", "torch")
    ),
    reason="neural-ctgan extra is not installed",
)
def test_ctgan_fit_sample_and_restore_nullable_columns(tmp_path: Path) -> None:
    training = tmp_path / "training.csv"
    _write_training(training)
    dataset = _dataset_contract()
    adapter = CtganAdapter()
    experiment = tmp_path / "experiment"

    manifest = adapter.fit(
        training,
        dataset,
        experiment,
        experiment / "model",
        FitConfig(
            seed="ctgan-fit",
            hyperparameters={"epochs": 1, "batch_size": 20, "pac": 10},
        ),
    )
    first = adapter.sample(
        manifest,
        experiment,
        experiment / "first.csv",
        row_count=20,
        seed="ctgan-sample",
    )
    second = adapter.sample(
        manifest,
        experiment,
        experiment / "second.csv",
        row_count=20,
        seed="ctgan-sample",
    )

    assert manifest.artifact_format == "pickle"
    assert manifest.dependency_license == "BUSL-1.1"
    assert manifest.transform_metadata["age"]["null_helper"]
    assert manifest.transform_metadata["segment"]["null_sentinel"]
    assert first.sha256 == second.sha256
    with (experiment / "first.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 20
    assert tuple(rows[0]) == dataset.column_names


@pytest.mark.skipif(
    importlib.util.find_spec("numpy") is None or importlib.util.find_spec("tensorflow") is None,
    reason="neural-tensorflow extra is not installed",
)
def test_tensorflow_gan_fit_sample_and_safe_generator_artifact(tmp_path: Path) -> None:
    training = tmp_path / "training.csv"
    _write_training(training)
    dataset = _dataset_contract()
    adapter = TensorflowGanAdapter()
    experiment = tmp_path / "experiment"

    manifest = adapter.fit(
        training,
        dataset,
        experiment,
        experiment / "model",
        FitConfig(
            seed="tensorflow-fit",
            hyperparameters={
                "epochs": 1,
                "batch_size": 16,
                "latent_dim": 8,
                "hidden_dim": 16,
            },
        ),
    )
    first = adapter.sample(
        manifest,
        experiment,
        experiment / "first.csv",
        row_count=20,
        seed="tensorflow-sample",
    )
    second = adapter.sample(
        manifest,
        experiment,
        experiment / "second.csv",
        row_count=20,
        seed="tensorflow-sample",
    )

    assert manifest.artifact_format == "keras_v3"
    assert manifest.dependency_license == "Apache-2.0"
    assert first.sha256 == second.sha256
    with (experiment / "first.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 20
    assert tuple(rows[0]) == dataset.column_names


def _dataset_contract() -> DatasetContract:
    return DatasetContract(
        name="customers",
        columns=(
            ColumnContract(
                name="age",
                kind=ColumnKind.CONTINUOUS,
                nullable=True,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="segment",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )


def _write_training(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("age", "segment"), lineterminator="\n")
        writer.writeheader()
        for index in range(100):
            writer.writerow(
                {
                    "age": "" if index % 10 == 0 else 20 + index % 40,
                    "segment": ("standard", "premium", "business")[index % 3],
                }
            )


def _pearson(pairs: list[tuple[float, float]]) -> float:
    mean_x = math.fsum(left for left, _ in pairs) / len(pairs)
    mean_y = math.fsum(right for _, right in pairs) / len(pairs)
    numerator = math.fsum((left - mean_x) * (right - mean_y) for left, right in pairs)
    denominator = math.sqrt(
        math.fsum((left - mean_x) ** 2 for left, _ in pairs)
        * math.fsum((right - mean_y) ** 2 for _, right in pairs)
    )
    return numerator / denominator
