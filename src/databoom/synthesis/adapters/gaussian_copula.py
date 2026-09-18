"""Owned, bounded Gaussian-copula baseline for reviewed mixed-type CSV data."""

from __future__ import annotations

import csv
import heapq
import json
import math
import platform
import random
import time
from collections import Counter
from pathlib import Path
from statistics import NormalDist
from typing import Any

from databoom.synthesis.adapters.empirical import _require_output_path
from databoom.synthesis.contracts import (
    AdapterAvailability,
    ColumnKind,
    DatasetContract,
    DeterminismLevel,
    FitConfig,
    JsonScalar,
    ModelManifest,
    SampleArtifact,
    SynthesizerCapabilities,
)
from databoom.synthesis.io import (
    canonical_row,
    relative_to_root,
    resolve_within,
    sha256_file,
    stable_digest,
    stable_int_seed,
    write_json,
    write_model_json,
)

type CopulaValue = float | str | None
type CopulaRow = dict[str, CopulaValue]

_MAX_FEATURES = 512
_NORMAL = NormalDist()
_UNIT_EPSILON = 1e-12


class GaussianCopulaAdapter:
    """Fit empirical marginals and regularized latent rank dependence."""

    @property
    def capabilities(self) -> SynthesizerCapabilities:
        return SynthesizerCapabilities(
            name="gaussian-copula",
            implementation_version="1",
            supports_missing_values=True,
            determinism=DeterminismLevel.DETERMINISTIC,
            complexity_tier=2,
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
        sample_size, regularization = _validate_hyperparameters(config.hyperparameters)
        started = time.perf_counter()
        source_sha256 = sha256_file(training_csv)
        retained, training_row_count = _read_bounded_rows(
            training_csv,
            dataset,
            seed=config.seed,
            sample_size=sample_size,
        )
        if training_row_count < 3:
            raise ValueError("Gaussian copula training requires at least three rows")

        rows = [row for _, row in retained]
        columns, transform_metadata, feature_count = _fit_marginals(rows, dataset)
        if feature_count > _MAX_FEATURES:
            raise ValueError(
                f"copula feature count exceeds the experimental limit of {_MAX_FEATURES}"
            )
        latent_rows = _latent_rows(retained, dataset, columns, seed=config.seed)
        correlation = _regularized_correlation(latent_rows, regularization)
        cholesky = _cholesky(correlation)
        if sha256_file(training_csv) != source_sha256:
            raise ValueError("training CSV changed while fitting the Gaussian copula")

        model_path = _require_output_path(
            experiment_root,
            model_dir / "gaussian-copula-model.json",
        )
        payload = {
            "model_version": "1",
            "adapter": self.capabilities.name,
            "training_row_count": training_row_count,
            "retained_row_count": len(rows),
            "sample_size": sample_size,
            "regularization": regularization,
            "columns": columns,
            "correlation": correlation,
            "cholesky": cholesky,
        }
        _validate_model_payload(payload, dataset)
        write_json(model_path, payload)
        artifact_sha256 = sha256_file(model_path)
        manifest = ModelManifest(
            model_id="model_"
            + stable_digest(
                self.capabilities.name,
                source_sha256,
                dataset.model_dump_json(),
                config.model_dump_json(),
                artifact_sha256,
            )[:24],
            adapter_name=self.capabilities.name,
            adapter_version=self.capabilities.implementation_version,
            dependency_versions={"python": platform.python_version()},
            dependency_license="PSF-2.0",
            training_partition_sha256=source_sha256,
            dataset_contract=dataset,
            hyperparameters={
                "sample_size": sample_size,
                "regularization": regularization,
            },
            seed=config.seed,
            fit_seconds=time.perf_counter() - started,
            artifact_format="json",
            artifact_path=relative_to_root(experiment_root, model_path),
            artifact_sha256=artifact_sha256,
            transform_metadata=transform_metadata,
            warnings=(
                "The copula stores bounded raw marginal values from columns explicitly "
                "classified non-sensitive; protect it as source-derived data.",
                "Frequency-then-lexical ordering is only a deterministic approximation "
                "for nominal categories.",
                "This experimental model has not passed production privacy, utility, "
                "calibration, or release gates.",
            ),
        )
        write_model_json(model_path.parent / "model-manifest.json", manifest)
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
        _validate_model_payload(payload, manifest.dataset_contract)

        output_path = _require_output_path(experiment_root, output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        stream = random.Random(
            stable_int_seed(seed, self.capabilities.name, manifest.model_id, "sample")
        )
        columns = payload["columns"]
        cholesky = payload["cholesky"]
        dimension = len(cholesky)
        started = time.perf_counter()
        try:
            with temporary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=manifest.dataset_contract.column_names,
                    lineterminator="\n",
                )
                writer.writeheader()
                for _ in range(row_count):
                    independent = [stream.normalvariate(0.0, 1.0) for _ in range(dimension)]
                    latent = [
                        math.fsum(
                            cholesky[index][source] * independent[source]
                            for source in range(index + 1)
                        )
                        for index in range(dimension)
                    ]
                    uniforms = [_clamp_unit(_NORMAL.cdf(value)) for value in latent]
                    output: dict[str, str] = {}
                    for contract in manifest.dataset_contract.columns:
                        settings = columns[contract.name]
                        missingness_index = settings["missingness_index"]
                        if missingness_index is not None and uniforms[missingness_index] >= (
                            1.0 - settings["null_rate"]
                        ):
                            output[contract.name] = ""
                            continue
                        values = settings["values"]
                        value_index = min(
                            int(uniforms[settings["value_index"]] * len(values)),
                            len(values) - 1,
                        )
                        value = values[value_index]
                        output[contract.name] = (
                            format(value, ".17g")
                            if contract.kind == ColumnKind.CONTINUOUS
                            else value
                        )
                    writer.writerow(output)
            temporary.replace(output_path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return SampleArtifact(
            path=relative_to_root(experiment_root, output_path),
            row_count=row_count,
            seed=seed,
            sample_seconds=time.perf_counter() - started,
            sha256=sha256_file(output_path),
        )


def _validate_hyperparameters(values: dict[str, Any]) -> tuple[int, float]:
    known = {"sample_size", "regularization"}
    unknown = set(values) - known
    if unknown:
        raise ValueError(
            "unsupported Gaussian-copula hyperparameters: " + ", ".join(sorted(unknown))
        )
    raw_sample_size = values.get("sample_size", 10_000)
    if isinstance(raw_sample_size, bool) or not isinstance(raw_sample_size, int):
        raise ValueError("sample_size must be an integer")
    if not 10 <= raw_sample_size <= 100_000:
        raise ValueError("sample_size must be between 10 and 100000")
    raw_regularization = values.get("regularization", 0.05)
    if isinstance(raw_regularization, bool) or not isinstance(
        raw_regularization, (int, float)
    ):
        raise ValueError("regularization must be a finite number")
    regularization = float(raw_regularization)
    if not math.isfinite(regularization) or not 0.0 < regularization <= 1.0:
        raise ValueError("regularization must be greater than 0 and at most 1")
    return raw_sample_size, regularization


def _read_bounded_rows(
    path: Path,
    dataset: DatasetContract,
    *,
    seed: str,
    sample_size: int,
) -> tuple[list[tuple[int, CopulaRow]], int]:
    heap: list[tuple[int, int, CopulaRow]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = tuple(reader.fieldnames or ())
        if actual != dataset.column_names:
            raise ValueError(
                "CSV columns must exactly match the reviewed dataset contract in order: "
                f"expected {dataset.column_names}, received {actual}"
            )
        row_count = 0
        contracts = {column.name: column for column in dataset.columns}
        for row_number, raw_row in enumerate(reader, start=2):
            if None in raw_row or any(raw_row[name] is None for name in dataset.column_names):
                raise ValueError(f"training CSV row {row_number} has the wrong number of values")
            normalized: CopulaRow = {}
            for name in dataset.column_names:
                raw_value = raw_row[name]
                if not isinstance(raw_value, str):
                    raise ValueError(
                        f"training CSV row {row_number} has an invalid {name!r} value"
                    )
                contract = contracts[name]
                if raw_value == "":
                    if not contract.nullable:
                        raise ValueError(
                            f"non-nullable column contains null values: {contract.name}"
                        )
                    normalized[name] = None
                elif contract.kind == ColumnKind.CONTINUOUS:
                    try:
                        value = float(raw_value)
                    except ValueError as exc:
                        raise ValueError(
                            f"continuous column is not numeric: {contract.name}"
                        ) from exc
                    if not math.isfinite(value):
                        raise ValueError(
                            f"continuous column contains a non-finite value: {contract.name}"
                        )
                    normalized[name] = value
                else:
                    normalized[name] = raw_value
            row_index = row_count
            row_count += 1
            priority = int(
                stable_digest(
                    seed,
                    str(row_index),
                    canonical_row(dataset.column_names, normalized),
                ),
                16,
            )
            entry = (-priority, -row_index, normalized)
            if len(heap) < sample_size:
                heapq.heappush(heap, entry)
            elif entry > heap[0]:
                heapq.heapreplace(heap, entry)
    retained = [(-entry[1], entry[2]) for entry in sorted(heap, reverse=True)]
    return retained, row_count


def _fit_marginals(
    rows: list[CopulaRow],
    dataset: DatasetContract,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, JsonScalar]], int]:
    columns: dict[str, dict[str, Any]] = {}
    transform_metadata: dict[str, dict[str, JsonScalar]] = {}
    feature_index = 0
    for contract in dataset.columns:
        observed = [row[contract.name] for row in rows if row[contract.name] is not None]
        if not observed:
            raise ValueError(f"training column contains no non-null values: {contract.name}")
        if contract.kind == ColumnKind.CONTINUOUS:
            values: list[float] | list[str] = sorted(float(value) for value in observed)
            ordering = "numeric"
        else:
            counts = Counter(str(value) for value in observed)
            ordered_counts = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            values = [value for value, count in ordered_counts for _ in range(count)]
            ordering = "frequency_then_lexical"
        null_count = len(rows) - len(observed)
        missingness_index = feature_index + 1 if contract.nullable else None
        columns[contract.name] = {
            "kind": contract.kind.value,
            "nullable": contract.nullable,
            "values": values,
            "observed_count": len(observed),
            "null_count": null_count,
            "null_rate": null_count / len(rows),
            "ordering": ordering,
            "value_index": feature_index,
            "missingness_index": missingness_index,
        }
        transform_metadata[contract.name] = {
            "kind": contract.kind.value,
            "ordering": ordering,
            "value_index": feature_index,
            "missingness_index": missingness_index,
            "marginal_observation_count": len(observed),
            "null_rate": null_count / len(rows),
        }
        feature_index += 2 if contract.nullable else 1
    return columns, transform_metadata, feature_index


def _latent_rows(
    retained: list[tuple[int, CopulaRow]],
    dataset: DatasetContract,
    columns: dict[str, dict[str, Any]],
    *,
    seed: str,
) -> list[list[float]]:
    intervals = {
        column.name: _marginal_intervals(columns[column.name]["values"])
        for column in dataset.columns
    }
    latent_rows: list[list[float]] = []
    for row_index, row in retained:
        encoded: list[float] = []
        for contract in dataset.columns:
            settings = columns[contract.name]
            value = row[contract.name]
            value_jitter = _stable_unit(seed, str(row_index), contract.name, "value")
            if value is None:
                value_uniform = value_jitter
            else:
                lower, upper = intervals[contract.name][value]
                value_uniform = (lower + value_jitter * (upper - lower)) / len(
                    settings["values"]
                )
            encoded.append(_NORMAL.inv_cdf(_clamp_unit(value_uniform)))
            if contract.nullable:
                missing_jitter = _stable_unit(
                    seed,
                    str(row_index),
                    contract.name,
                    "missingness",
                )
                non_null_count = settings["observed_count"]
                if value is None:
                    missing_uniform = (
                        non_null_count + missing_jitter * settings["null_count"]
                    ) / len(retained)
                else:
                    missing_uniform = missing_jitter * non_null_count / len(retained)
                encoded.append(_NORMAL.inv_cdf(_clamp_unit(missing_uniform)))
        latent_rows.append(encoded)
    return latent_rows


def _marginal_intervals(values: list[float] | list[str]) -> dict[float | str, tuple[int, int]]:
    intervals: dict[float | str, tuple[int, int]] = {}
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[end] == values[start]:
            end += 1
        intervals[values[start]] = (start, end)
        start = end
    return intervals


def _regularized_correlation(rows: list[list[float]], regularization: float) -> list[list[float]]:
    dimension = len(rows[0])
    means = [math.fsum(row[index] for row in rows) / len(rows) for index in range(dimension)]
    sums_of_squares = [
        math.fsum((row[index] - means[index]) ** 2 for row in rows)
        for index in range(dimension)
    ]
    correlation = [[0.0] * dimension for _ in range(dimension)]
    for left in range(dimension):
        correlation[left][left] = 1.0
        for right in range(left):
            denominator = math.sqrt(sums_of_squares[left] * sums_of_squares[right])
            raw = (
                math.fsum(
                    (row[left] - means[left]) * (row[right] - means[right])
                    for row in rows
                )
                / denominator
                if denominator > 0
                else 0.0
            )
            value = (1.0 - regularization) * max(-1.0, min(1.0, raw))
            correlation[left][right] = value
            correlation[right][left] = value
    return correlation


def _cholesky(matrix: list[list[float]]) -> list[list[float]]:
    dimension = len(matrix)
    factor = [[0.0] * dimension for _ in range(dimension)]
    for row in range(dimension):
        for column in range(row + 1):
            residual = matrix[row][column] - math.fsum(
                factor[row][index] * factor[column][index] for index in range(column)
            )
            if row == column:
                if not math.isfinite(residual) or residual <= 0.0:
                    raise ValueError(
                        "regularized copula correlation matrix is not positive definite"
                    )
                factor[row][column] = math.sqrt(residual)
            else:
                factor[row][column] = residual / factor[column][column]
            if not math.isfinite(factor[row][column]):
                raise ValueError("copula Cholesky factor contains a non-finite value")
    return factor


def _validate_model_payload(payload: Any, dataset: DatasetContract) -> None:
    if not isinstance(payload, dict):
        raise ValueError("copula model payload must be a JSON object")
    if payload.get("model_version") != "1" or payload.get("adapter") != "gaussian-copula":
        raise ValueError("unsupported Gaussian-copula model payload")
    training_count = _required_integer(payload, "training_row_count", minimum=3)
    retained_count = _required_integer(payload, "retained_row_count", minimum=3)
    sample_size = _required_integer(payload, "sample_size", minimum=10)
    if sample_size > 100_000:
        raise ValueError("copula sample size exceeds its supported bound")
    if retained_count > training_count or retained_count > sample_size:
        raise ValueError("copula retained row count exceeds its declared bound")
    regularization = _required_float(payload, "regularization")
    if not 0.0 < regularization <= 1.0:
        raise ValueError("copula regularization is outside its supported range")

    columns = payload.get("columns")
    if not isinstance(columns, dict) or set(columns) != set(dataset.column_names):
        raise ValueError("copula model columns do not match the reviewed dataset contract")
    expected_index = 0
    for contract in dataset.columns:
        settings = columns[contract.name]
        if not isinstance(settings, dict):
            raise ValueError(f"copula column settings are invalid: {contract.name}")
        if settings.get("kind") != contract.kind.value or settings.get("nullable") is not (
            contract.nullable
        ):
            raise ValueError(f"copula column contract mismatch: {contract.name}")
        values = settings.get("values")
        if not isinstance(values, list) or not values or len(values) > retained_count:
            raise ValueError(f"copula marginal values are invalid: {contract.name}")
        for value in values:
            if contract.kind == ColumnKind.CONTINUOUS:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"copula numeric marginal is invalid: {contract.name}")
                if not math.isfinite(float(value)):
                    raise ValueError(f"copula numeric marginal is non-finite: {contract.name}")
            elif not isinstance(value, str) or value == "":
                raise ValueError(f"copula categorical marginal is invalid: {contract.name}")
        if contract.kind == ColumnKind.CONTINUOUS and values != sorted(values):
            raise ValueError(f"copula numeric marginal is not ordered: {contract.name}")
        if contract.kind == ColumnKind.DISCRETE and not _has_valid_discrete_order(values):
            raise ValueError(f"copula categorical marginal is not ordered: {contract.name}")
        observed_count = _required_integer(settings, "observed_count", minimum=1)
        null_count = _required_integer(settings, "null_count", minimum=0)
        if observed_count != len(values) or observed_count + null_count != retained_count:
            raise ValueError(f"copula marginal counts are inconsistent: {contract.name}")
        if not contract.nullable and null_count:
            raise ValueError(f"copula non-nullable column records nulls: {contract.name}")
        null_rate = _required_float(settings, "null_rate")
        if not 0.0 <= null_rate < 1.0 or not math.isclose(
            null_rate,
            null_count / retained_count,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError(f"copula null rate is invalid: {contract.name}")
        if settings.get("value_index") != expected_index:
            raise ValueError(f"copula value feature index is invalid: {contract.name}")
        expected_missingness = expected_index + 1 if contract.nullable else None
        if settings.get("missingness_index") != expected_missingness:
            raise ValueError(f"copula missingness feature index is invalid: {contract.name}")
        expected_ordering = (
            "numeric" if contract.kind == ColumnKind.CONTINUOUS else "frequency_then_lexical"
        )
        if settings.get("ordering") != expected_ordering:
            raise ValueError(f"copula marginal ordering is invalid: {contract.name}")
        expected_index += 2 if contract.nullable else 1

    if expected_index > _MAX_FEATURES:
        raise ValueError("copula model exceeds the supported feature limit")
    correlation = _required_matrix(payload, "correlation", expected_index)
    cholesky = _required_matrix(payload, "cholesky", expected_index)
    for row in range(expected_index):
        if not math.isclose(correlation[row][row], 1.0, abs_tol=1e-10):
            raise ValueError("copula correlation diagonal must equal one")
        if cholesky[row][row] <= 0.0:
            raise ValueError("copula Cholesky diagonal must be positive")
        for column in range(expected_index):
            if not math.isclose(
                correlation[row][column],
                correlation[column][row],
                rel_tol=1e-10,
                abs_tol=1e-10,
            ):
                raise ValueError("copula correlation matrix must be symmetric")
            if column > row and cholesky[row][column] != 0.0:
                raise ValueError("copula Cholesky factor must be lower triangular")
    reconstructed = [
        [
            math.fsum(
                cholesky[row][index] * cholesky[column][index]
                for index in range(expected_index)
            )
            for column in range(expected_index)
        ]
        for row in range(expected_index)
    ]
    for row in range(expected_index):
        for column in range(expected_index):
            if not math.isclose(
                reconstructed[row][column],
                correlation[row][column],
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                raise ValueError("copula Cholesky factor does not match the correlation matrix")


def _required_integer(payload: dict[str, Any], name: str, *, minimum: int) -> int:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"copula model {name} is invalid")
    return value


def _has_valid_discrete_order(values: list[Any]) -> bool:
    counts = Counter(values)
    expected = [
        value
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        for _ in range(count)
    ]
    return values == expected


def _required_float(payload: dict[str, Any], name: str) -> float:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"copula model {name} is invalid")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"copula model {name} is non-finite")
    return result


def _required_matrix(payload: dict[str, Any], name: str, dimension: int) -> list[list[float]]:
    value = payload.get(name)
    if not isinstance(value, list) or len(value) != dimension:
        raise ValueError(f"copula {name} matrix has the wrong dimensions")
    matrix: list[list[float]] = []
    for raw_row in value:
        if not isinstance(raw_row, list) or len(raw_row) != dimension:
            raise ValueError(f"copula {name} matrix has the wrong dimensions")
        row = []
        for raw in raw_row:
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ValueError(f"copula {name} matrix contains an invalid value")
            numeric = float(raw)
            if not math.isfinite(numeric):
                raise ValueError(f"copula {name} matrix contains a non-finite value")
            row.append(numeric)
        matrix.append(row)
    return matrix


def _stable_unit(*parts: str) -> float:
    value = int(stable_digest(*parts), 16)
    return (value + 0.5) / (2**256)


def _clamp_unit(value: float) -> float:
    return max(_UNIT_EPSILON, min(1.0 - _UNIT_EPSILON, value))
