"""Optional CTGAN provider adapter with lazy ML imports.

Importing this module does not import pandas, NumPy, torch, or CTGAN. Those
dependencies are resolved only inside the dedicated worker's fit/sample methods.
"""

from __future__ import annotations

import importlib.util
import pickle
import platform
import random
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from databoom.synthesis.adapters.base import SynthesizerUnavailableError
from databoom.synthesis.adapters.empirical import _require_header, _require_output_path
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

_DEPENDENCIES = ("ctgan", "pandas", "numpy", "torch")


class CtganAdapter:
    """Wrap the maintained standalone CTGAN provider behind DataBoom contracts."""

    @property
    def capabilities(self) -> SynthesizerCapabilities:
        missing = [name for name in _DEPENDENCIES if importlib.util.find_spec(name) is None]
        available = not missing
        return SynthesizerCapabilities(
            name="ctgan",
            implementation_version="1",
            supports_conditions=False,
            supports_missing_values=True,
            determinism=DeterminismLevel.BEST_EFFORT,
            requires_gpu=False,
            complexity_tier=3,
            availability=(
                AdapterAvailability.AVAILABLE
                if available
                else AdapterAvailability.MISSING_DEPENDENCY
            ),
            dependency="ctgan",
            dependency_version=_package_version("ctgan") if available else None,
            dependency_license="BUSL-1.1",
            unavailable_reason=(
                None
                if available
                else f"install the neural-ctgan extra; missing: {', '.join(missing)}"
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
        import pandas as pd
        import torch
        from ctgan import CTGAN

        hyperparameters = _validate_hyperparameters(config.hyperparameters)
        seed_value = stable_int_seed(config.seed, self.capabilities.name, "fit")
        random.seed(seed_value)
        np.random.seed(seed_value)
        torch.manual_seed(seed_value)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed_value)

        frame = pd.read_csv(training_csv)
        _require_header(list(frame.columns), dataset)
        if frame.empty:
            raise ValueError("training partition is empty")
        transformed, discrete_columns, transform_metadata = _prepare_frame(frame, dataset, pd)

        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "ctgan-model.pkl"
        started = time.perf_counter()
        model = CTGAN(**hyperparameters)
        if hasattr(model, "set_random_state"):
            model.set_random_state(seed_value)
        model.fit(transformed, discrete_columns=list(discrete_columns))
        fit_seconds = time.perf_counter() - started

        with model_path.open("wb") as handle:
            pickle.dump(
                {
                    "model": model,
                    "columns": list(dataset.column_names),
                    "transform_metadata": transform_metadata,
                },
                handle,
                protocol=pickle.HIGHEST_PROTOCOL,
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
                **{name: _package_version(name) for name in _DEPENDENCIES},
            },
            dependency_license="BUSL-1.1",
            training_partition_sha256=sha256_file(training_csv),
            dataset_contract=dataset,
            hyperparameters=hyperparameters,
            seed=config.seed,
            fit_seconds=fit_seconds,
            artifact_format="pickle",
            artifact_path=relative_to_root(experiment_root, model_path),
            artifact_sha256=artifact_sha256,
            transform_metadata=transform_metadata,
            warnings=(
                "The maintained ctgan provider is BUSL-1.1; distribution and commercial use "
                "require an explicit licensing review.",
                "The model is a local Python pickle. Load it only in an isolated worker after "
                "checksum verification; never accept untrusted model files.",
                "A fitted CTGAN is an experimental candidate, not evidence of anonymity "
                "or release approval.",
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
        import pandas as pd

        model_path = resolve_within(experiment_root, manifest.artifact_path)
        if sha256_file(model_path) != manifest.artifact_sha256:
            raise ValueError("model artifact checksum mismatch")

        # Pickle is executable input. This path is restricted to a checksummed,
        # locally produced experiment artifact; it is not an untrusted import API.
        with model_path.open("rb") as handle:
            payload = pickle.load(handle)  # noqa: S301
        model = payload["model"]
        seed_value = stable_int_seed(seed, self.capabilities.name, "sample")
        if hasattr(model, "set_random_state"):
            model.set_random_state(seed_value)
        started = time.perf_counter()
        synthetic = model.sample(row_count)
        synthetic = _restore_frame(
            synthetic,
            payload["columns"],
            payload["transform_metadata"],
            pd,
        )
        output_path = _require_output_path(experiment_root, output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        synthetic.to_csv(temporary, index=False, lineterminator="\n")
        temporary.replace(output_path)
        elapsed = time.perf_counter() - started
        return SampleArtifact(
            path=relative_to_root(experiment_root, output_path),
            row_count=row_count,
            seed=seed,
            sample_seconds=elapsed,
            sha256=sha256_file(output_path),
        )

    def _require_available(self) -> None:
        capabilities = self.capabilities
        if capabilities.availability != AdapterAvailability.AVAILABLE:
            raise SynthesizerUnavailableError(
                capabilities.unavailable_reason or "CTGAN unavailable"
            )


def _validate_hyperparameters(values: dict[str, JsonScalar]) -> dict[str, Any]:
    defaults: dict[str, int | bool] = {
        "epochs": 300,
        "batch_size": 500,
        "pac": 10,
        "verbose": False,
    }
    unknown = set(values) - set(defaults)
    if unknown:
        raise ValueError(f"unsupported CTGAN hyperparameters: {', '.join(sorted(unknown))}")
    result = {**defaults, **values}
    for name in ("epochs", "batch_size", "pac"):
        value = result[name]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"CTGAN {name} must be a positive integer")
    if result["batch_size"] % 2 or result["batch_size"] % result["pac"]:
        raise ValueError("CTGAN batch_size must be even and divisible by pac")
    if not isinstance(result["verbose"], bool):
        raise ValueError("CTGAN verbose must be a boolean")
    return result


def _prepare_frame(
    frame: Any, dataset: DatasetContract, pandas: Any
) -> tuple[Any, tuple[str, ...], dict[str, dict[str, JsonScalar]]]:
    transformed = frame.copy()
    discrete_columns: list[str] = []
    metadata: dict[str, dict[str, JsonScalar]] = {}
    occupied = set(transformed.columns)
    for column in dataset.columns:
        series = transformed[column.name]
        if column.kind.value == "discrete":
            sentinel = _unique_name(
                "__DATABOOM_NULL__", set(str(value) for value in series.dropna())
            )
            transformed[column.name] = series.astype("string").fillna(sentinel)
            discrete_columns.append(column.name)
            metadata[column.name] = {"kind": "discrete", "null_sentinel": sentinel}
            continue

        numeric = pandas.to_numeric(series, errors="raise")
        if numeric.dropna().empty:
            raise ValueError(f"continuous column contains no numeric values: {column.name}")
        helper = _unique_name(f"__databoom_null__{column.name}", occupied)
        occupied.add(helper)
        median = float(numeric.median())
        transformed[column.name] = numeric.fillna(median).astype(float)
        transformed[helper] = numeric.isna().map({True: "1", False: "0"})
        discrete_columns.append(helper)
        metadata[column.name] = {
            "kind": "continuous",
            "null_helper": helper,
            "imputation_value": median,
        }
    return transformed, tuple(discrete_columns), metadata


def _restore_frame(
    frame: Any, columns: list[str], metadata: dict[str, dict[str, Any]], pandas: Any
) -> Any:
    restored = frame.copy()
    for column, settings in metadata.items():
        if settings["kind"] == "discrete":
            restored[column] = restored[column].replace(settings["null_sentinel"], pandas.NA)
            continue
        helper = settings["null_helper"]
        null_mask = restored[helper].astype(str).str.lower().isin({"1", "1.0", "true"})
        restored.loc[null_mask, column] = pandas.NA
        restored = restored.drop(columns=[helper])
    return restored[columns]


def _unique_name(base: str, occupied: set[str]) -> str:
    candidate = base
    suffix = 1
    while candidate in occupied:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"
