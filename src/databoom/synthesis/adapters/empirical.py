"""Bounded independent empirical baseline for mixed-type tables."""

from __future__ import annotations

import csv
import json
import platform
import random
import time
from pathlib import Path
from typing import Any

from databoom.synthesis.contracts import (
    AdapterAvailability,
    DatasetContract,
    DeterminismLevel,
    FitConfig,
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


class IndependentEmpiricalAdapter:
    """Sample bounded per-column reservoirs as the owned source-trained baseline.

    This adapter intentionally does not claim joint fidelity. Its purpose is to
    establish a cheap, reproducible baseline that a neural candidate must beat.
    """

    @property
    def capabilities(self) -> SynthesizerCapabilities:
        return SynthesizerCapabilities(
            name="empirical-independent",
            implementation_version="1",
            supports_missing_values=True,
            determinism=DeterminismLevel.DETERMINISTIC,
            complexity_tier=1,
            availability=AdapterAvailability.AVAILABLE,
            dependency="Python standard library",
            dependency_version=platform.python_version(),
            dependency_license="PSF-2.0",
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
        started = time.perf_counter()
        reservoir_size = _integer_hyperparameter(
            config.hyperparameters,
            "reservoir_size",
            default=10_000,
            minimum=10,
            maximum=1_000_000,
        )
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / "empirical-model.json"

        states = {
            column.name: {
                "kind": column.kind.value,
                "nullable": column.nullable,
                "observed": 0,
                "null_count": 0,
                "values": [],
            }
            for column in dataset.columns
        }
        streams = {
            column.name: random.Random(
                stable_int_seed(config.seed, self.capabilities.name, column.name, "reservoir")
            )
            for column in dataset.columns
        }

        with training_csv.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            _require_header(reader.fieldnames, dataset)
            row_count = 0
            for row in reader:
                row_count += 1
                for column in dataset.columns:
                    state = states[column.name]
                    value = row[column.name]
                    if value == "":
                        state["null_count"] += 1
                        continue
                    state["observed"] += 1
                    _add_to_reservoir(
                        state["values"],
                        value,
                        int(state["observed"]),
                        reservoir_size,
                        streams[column.name],
                    )
        if row_count == 0:
            raise ValueError("training partition is empty")
        empty_columns = [name for name, state in states.items() if not state["values"]]
        if empty_columns:
            raise ValueError(
                f"training columns contain no non-null values: {', '.join(empty_columns)}"
            )

        payload = {
            "model_version": "1",
            "adapter": self.capabilities.name,
            "row_count": row_count,
            "reservoir_size": reservoir_size,
            "columns": states,
        }
        model_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        artifact_sha256 = sha256_file(model_path)
        fit_seconds = time.perf_counter() - started
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
            dependency_versions={"python": platform.python_version()},
            dependency_license="PSF-2.0",
            training_partition_sha256=sha256_file(training_csv),
            dataset_contract=dataset,
            hyperparameters={"reservoir_size": reservoir_size},
            seed=config.seed,
            fit_seconds=fit_seconds,
            artifact_format="json",
            artifact_path=relative_to_root(experiment_root, model_path),
            artifact_sha256=artifact_sha256,
            warnings=(
                "The empirical baseline stores bounded raw exemplars from columns explicitly "
                "classified non-sensitive; protect the model directory as source-derived data.",
                "Independent marginal sampling is a baseline and does not preserve "
                "joint structure.",
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
        model_path = resolve_within(experiment_root, manifest.artifact_path)
        if sha256_file(model_path) != manifest.artifact_sha256:
            raise ValueError("model artifact checksum mismatch")

        payload = json.loads(model_path.read_text(encoding="utf-8"))
        states = payload["columns"]
        streams = {
            column.name: random.Random(
                stable_int_seed(seed, self.capabilities.name, column.name, "sample")
            )
            for column in manifest.dataset_contract.columns
        }
        output_path = _require_output_path(experiment_root, output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        started = time.perf_counter()
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            columns = manifest.dataset_contract.column_names
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            for _ in range(row_count):
                output_row: dict[str, str] = {}
                for column in manifest.dataset_contract.columns:
                    state = states[column.name]
                    stream = streams[column.name]
                    total = int(state["observed"]) + int(state["null_count"])
                    null_rate = int(state["null_count"]) / total if total else 0.0
                    if column.nullable and stream.random() < null_rate:
                        output_row[column.name] = ""
                    else:
                        output_row[column.name] = stream.choice(state["values"])
                writer.writerow(output_row)
        temporary.replace(output_path)
        elapsed = time.perf_counter() - started
        return SampleArtifact(
            path=relative_to_root(experiment_root, output_path),
            row_count=row_count,
            seed=seed,
            sample_seconds=elapsed,
            sha256=sha256_file(output_path),
        )


def _add_to_reservoir(
    values: list[str],
    value: str,
    observed: int,
    capacity: int,
    stream: random.Random,
) -> None:
    if len(values) < capacity:
        values.append(value)
        return
    replacement = stream.randrange(observed)
    if replacement < capacity:
        values[replacement] = value


def _integer_hyperparameter(
    values: dict[str, Any],
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    unknown = set(values) - {name}
    if unknown:
        raise ValueError(f"unsupported empirical hyperparameters: {', '.join(sorted(unknown))}")
    raw = values.get(name, default)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= raw <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return raw


def _require_header(fieldnames: list[str] | None, dataset: DatasetContract) -> None:
    actual = tuple(fieldnames or ())
    if actual != dataset.column_names:
        raise ValueError(
            "CSV columns must exactly match the reviewed dataset contract in order: "
            f"expected {dataset.column_names}, received {actual}"
        )


def _require_output_path(experiment_root: Path, output_path: Path) -> Path:
    resolved_root = experiment_root.resolve()
    resolved = output_path.resolve()
    if resolved_root not in resolved.parents:
        raise ValueError("sample output path must be inside the experiment root")
    return resolved
