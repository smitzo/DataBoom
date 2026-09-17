"""Optional scikit-learn Gaussian-mixture synthesis baseline."""

from __future__ import annotations

import importlib.util
import json
import platform
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from databoom.synthesis.adapters.base import SynthesizerUnavailableError
from databoom.synthesis.adapters.empirical import _require_output_path
from databoom.synthesis.adapters.tabular_encoding import decode_rows, encode_csv, write_rows
from databoom.synthesis.contracts import (
    AdapterAvailability,
    DatasetContract,
    DeterminismLevel,
    FitConfig,
    JsonScalar,
    ModelManifest,
    SampleArtifact,
    SynthesizerCapabilities,
)
from databoom.synthesis.io import (
    relative_to_root,
    resolve_within,
    sha256_file,
    stable_digest,
    stable_int_seed,
    write_model_json,
)

_DEPENDENCIES = ("numpy", "sklearn")


class SklearnGaussianMixtureAdapter:
    """Fit a classical joint baseline and persist only numeric JSON parameters."""

    @property
    def capabilities(self) -> SynthesizerCapabilities:
        missing = [name for name in _DEPENDENCIES if importlib.util.find_spec(name) is None]
        return SynthesizerCapabilities(
            name="sklearn-gaussian-mixture",
            implementation_version="1",
            supports_missing_values=True,
            determinism=DeterminismLevel.DETERMINISTIC,
            complexity_tier=2,
            availability=(
                AdapterAvailability.AVAILABLE
                if not missing
                else AdapterAvailability.MISSING_DEPENDENCY
            ),
            dependency="scikit-learn",
            dependency_version=_package_version("scikit-learn") if not missing else None,
            dependency_license="BSD-3-Clause",
            unavailable_reason=(
                None
                if not missing
                else f"install the ml-sklearn extra; missing: {', '.join(missing)}"
            ),
        )

    def fit(
        self,
        training_csv: Path,
        dataset: DatasetContract,
        experiment_root: Path,
        model_dir: Path,
        config: FitConfig,
    ) -> ModelManifest:
        dataset.require_training_eligible()
        self._require_available()
        import numpy as np
        from sklearn.mixture import GaussianMixture

        matrix, transform_metadata = encode_csv(training_csv, dataset, np)
        parameters = _validate_hyperparameters(config.hyperparameters, len(matrix))
        seed_value = stable_int_seed(config.seed, self.capabilities.name, "fit") % (2**32 - 1)
        model = GaussianMixture(random_state=seed_value, **parameters)
        started = time.perf_counter()
        model.fit(matrix)
        fit_seconds = time.perf_counter() - started
        if not model.converged_:
            raise RuntimeError("scikit-learn Gaussian mixture did not converge")

        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "sklearn-gmm-model.json"
        payload = {
            "model_version": "1",
            "covariance_type": model.covariance_type,
            "weights": model.weights_.tolist(),
            "means": model.means_.tolist(),
            "covariances": model.covariances_.tolist(),
            "transform_metadata": transform_metadata,
            "converged": bool(model.converged_),
            "iterations": int(model.n_iter_),
            "lower_bound": float(model.lower_bound_),
        }
        model_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        artifact_sha256 = sha256_file(model_path)
        manifest = ModelManifest(
            model_id="model_"
            + stable_digest(
                self.capabilities.name,
                sha256_file(training_csv),
                dataset.model_dump_json(),
                config.model_dump_json(),
                artifact_sha256,
            )[:24],
            adapter_name=self.capabilities.name,
            adapter_version=self.capabilities.implementation_version,
            dependency_versions={
                "python": platform.python_version(),
                "numpy": _package_version("numpy"),
                "scikit-learn": _package_version("scikit-learn"),
            },
            dependency_license="BSD-3-Clause",
            training_partition_sha256=sha256_file(training_csv),
            dataset_contract=dataset,
            hyperparameters=parameters,
            seed=config.seed,
            fit_seconds=fit_seconds,
            artifact_format="json",
            artifact_path=relative_to_root(experiment_root, model_path),
            artifact_sha256=artifact_sha256,
            transform_metadata=transform_metadata,
            warnings=(
                "Gaussian mixtures are an experimental single-table baseline and may smooth "
                "rare modes or invalid feature combinations.",
                "This model has not passed production privacy, utility, or release gates.",
            ),
        )
        write_model_json(model_dir / "model-manifest.json", manifest)
        return manifest

    def sample(
        self,
        manifest: ModelManifest,
        experiment_root: Path,
        output_path: Path,
        *,
        row_count: int,
        seed: str,
    ) -> SampleArtifact:
        if row_count <= 0:
            raise ValueError("sample row count must be positive")
        if manifest.adapter_name != self.capabilities.name:
            raise ValueError("model manifest belongs to a different adapter")
        self._require_available()
        import numpy as np

        model_path = resolve_within(experiment_root, manifest.artifact_path)
        if sha256_file(model_path) != manifest.artifact_sha256:
            raise ValueError("model artifact checksum mismatch")
        payload = json.loads(model_path.read_text(encoding="utf-8"))
        started = time.perf_counter()
        encoded = _sample_parameters(payload, row_count, seed, np)
        rows = decode_rows(
            encoded,
            manifest.dataset_contract,
            payload["transform_metadata"],
            np,
        )
        output_path = _require_output_path(experiment_root, output_path)
        write_rows(output_path, manifest.dataset_contract, rows)
        return SampleArtifact(
            path=relative_to_root(experiment_root, output_path),
            row_count=row_count,
            seed=seed,
            sample_seconds=time.perf_counter() - started,
            sha256=sha256_file(output_path),
        )

    def _require_available(self) -> None:
        capabilities = self.capabilities
        if capabilities.availability != AdapterAvailability.AVAILABLE:
            raise SynthesizerUnavailableError(
                capabilities.unavailable_reason or "scikit-learn provider unavailable"
            )


def _validate_hyperparameters(values: dict[str, JsonScalar], row_count: int) -> dict[str, Any]:
    defaults: dict[str, int | float | str] = {
        "n_components": min(5, row_count),
        "covariance_type": "diag",
        "max_iter": 200,
        "reg_covar": 1e-6,
    }
    unknown = set(values) - set(defaults)
    if unknown:
        raise ValueError(f"unsupported scikit-learn hyperparameters: {', '.join(sorted(unknown))}")
    result = {**defaults, **values}
    components = result["n_components"]
    if isinstance(components, bool) or not isinstance(components, int):
        raise ValueError("n_components must be an integer")
    if not 1 <= components <= min(row_count, 64):
        raise ValueError("n_components must be between 1 and min(training rows, 64)")
    covariance_type = result["covariance_type"]
    if covariance_type not in {"diag", "full"}:
        raise ValueError("covariance_type must be 'diag' or 'full'")
    max_iter = result["max_iter"]
    if isinstance(max_iter, bool) or not isinstance(max_iter, int) or not 1 <= max_iter <= 10_000:
        raise ValueError("max_iter must be an integer between 1 and 10000")
    reg_covar = result["reg_covar"]
    if isinstance(reg_covar, bool) or not isinstance(reg_covar, (int, float)):
        raise ValueError("reg_covar must be numeric")
    if not 0 < float(reg_covar) <= 1:
        raise ValueError("reg_covar must be greater than 0 and at most 1")
    return result


def _sample_parameters(payload: dict[str, Any], row_count: int, seed: str, numpy: Any) -> Any:
    rng = numpy.random.default_rng(
        stable_int_seed(seed, "sklearn-gaussian-mixture", "sample") % (2**63 - 1)
    )
    weights = numpy.asarray(payload["weights"], dtype="float64")
    means = numpy.asarray(payload["means"], dtype="float64")
    covariances = numpy.asarray(payload["covariances"], dtype="float64")
    components = rng.choice(len(weights), size=row_count, p=weights / weights.sum())
    samples = numpy.empty((row_count, means.shape[1]), dtype="float64")
    for component in range(len(weights)):
        indexes = numpy.flatnonzero(components == component)
        if not len(indexes):
            continue
        if payload["covariance_type"] == "diag":
            samples[indexes] = rng.normal(
                loc=means[component],
                scale=numpy.sqrt(numpy.maximum(covariances[component], 1e-12)),
                size=(len(indexes), means.shape[1]),
            )
        else:
            samples[indexes] = rng.multivariate_normal(
                means[component], covariances[component], size=len(indexes)
            )
    return samples


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"
