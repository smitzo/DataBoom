"""Dependency-light quality and exact-copy evaluation for tabular candidates."""

from __future__ import annotations

import csv
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from databoom.synthesis.contracts import (
    ColumnKind,
    DatasetContract,
    EvaluationPolicy,
    GateResult,
    GateStatus,
    MetricResult,
    ModelManifest,
    QualityReport,
    SampleArtifact,
)
from databoom.synthesis.io import canonical_row, stable_digest

_NULL_CATEGORY = "__DATABOOM_EVALUATION_NULL__"


@dataclass
class _DatasetStats:
    row_count: int
    header_matches: bool
    invalid_value_count: int
    row_hashes: list[str]
    numeric: dict[str, list[float]]
    categorical: dict[str, Counter[str]]


def evaluate_candidate(
    *,
    adapter_name: str,
    dataset: DatasetContract,
    training_csv: Path,
    holdout_csv: Path,
    synthetic_csv: Path,
    expected_sample_rows: int,
    reproducible_sample: bool,
    model_manifest: ModelManifest,
    sample_artifact: SampleArtifact,
    policy: EvaluationPolicy,
) -> QualityReport:
    """Build a multidimensional report without collapsing hard gates into one score."""

    holdout = _read_stats(holdout_csv, dataset)
    synthetic = _read_stats(synthetic_csv, dataset)
    training_hashes = _read_row_hashes(training_csv, dataset.column_names)
    metrics: list[MetricResult] = []

    metrics.extend(
        (
            _boolean_metric(
                "columns_match_contract",
                "structural",
                holdout.header_matches and synthetic.header_matches,
            ),
            _boolean_metric(
                "sample_row_count_matches",
                "structural",
                synthetic.row_count == expected_sample_rows,
            ),
            _boolean_metric(
                "values_parse_and_respect_nullability",
                "structural",
                holdout.invalid_value_count == 0 and synthetic.invalid_value_count == 0,
            ),
        )
    )

    fidelity_names: list[str] = []
    for column in dataset.columns:
        if column.kind == ColumnKind.CONTINUOUS:
            reference = holdout.numeric[column.name]
            generated = synthetic.numeric[column.name]
            ks_name = f"numeric_ks:{column.name}"
            mean_name = f"normalized_mean_error:{column.name}"
            fidelity_names.extend((ks_name, mean_name))
            if not reference or not generated:
                metrics.extend(
                    (
                        MetricResult(
                            name=ks_name,
                            dimension="fidelity",
                            value=None,
                            threshold=policy.maximum_numeric_ks,
                            status=GateStatus.NOT_EVALUATED,
                            column=column.name,
                            detail=(
                                "numeric comparison requires non-null reference and "
                                "synthetic values"
                            ),
                        ),
                        MetricResult(
                            name=mean_name,
                            dimension="fidelity",
                            value=None,
                            threshold=policy.maximum_normalized_mean_error,
                            status=GateStatus.NOT_EVALUATED,
                            column=column.name,
                            detail=(
                                "numeric comparison requires non-null reference and "
                                "synthetic values"
                            ),
                        ),
                    )
                )
                continue
            ks_value = _ks_statistic(reference, generated)
            mean_error = _normalized_mean_error(reference, generated)
            metrics.extend(
                (
                    _maximum_metric(
                        ks_name,
                        "fidelity",
                        ks_value,
                        policy.maximum_numeric_ks,
                        column.name,
                    ),
                    _maximum_metric(
                        mean_name,
                        "fidelity",
                        mean_error,
                        policy.maximum_normalized_mean_error,
                        column.name,
                    ),
                )
            )
        else:
            name = f"categorical_tv:{column.name}"
            fidelity_names.append(name)
            tv_value = _total_variation(
                holdout.categorical[column.name],
                synthetic.categorical[column.name],
            )
            metrics.append(
                _maximum_metric(
                    name,
                    "fidelity",
                    tv_value,
                    policy.maximum_categorical_tv,
                    column.name,
                )
            )

    synthetic_hashes = synthetic.row_hashes
    uniqueness = len(set(synthetic_hashes)) / len(synthetic_hashes) if synthetic_hashes else 0.0
    exact_matches = sum(row_hash in training_hashes for row_hash in synthetic_hashes)
    exact_match_rate = exact_matches / len(synthetic_hashes) if synthetic_hashes else 1.0
    metrics.extend(
        (
            _minimum_metric(
                "synthetic_uniqueness",
                "diversity",
                uniqueness,
                policy.minimum_synthetic_uniqueness,
            ),
            _maximum_metric(
                "exact_training_match_rate",
                "privacy",
                exact_match_rate,
                policy.maximum_exact_training_match_rate,
            ),
            _boolean_metric(
                "sample_reproducible",
                "reproducibility",
                reproducible_sample,
                required=policy.require_reproducible_sample,
            ),
            MetricResult(
                name="fit_seconds",
                dimension="performance",
                value=model_manifest.fit_seconds,
                status=GateStatus.PASSED,
            ),
            MetricResult(
                name="sample_seconds",
                dimension="performance",
                value=sample_artifact.sample_seconds,
                status=GateStatus.PASSED,
            ),
        )
    )

    gates = (
        _gate(
            "structural_validity",
            metrics,
            (
                "columns_match_contract",
                "sample_row_count_matches",
                "values_parse_and_respect_nullability",
            ),
        ),
        _gate("fidelity", metrics, tuple(fidelity_names)),
        _gate("diversity", metrics, ("synthetic_uniqueness",)),
        _gate("exact_copy_privacy", metrics, ("exact_training_match_rate",)),
        _gate("reproducibility", metrics, ("sample_reproducible",)),
        GateResult(
            name="production_evidence",
            status=GateStatus.NOT_EVALUATED,
            detail=(
                "downstream utility, privacy attacks, calibrated thresholds, signed lineage, "
                "and isolated production workers are not complete"
            ),
        ),
    )
    return QualityReport(
        adapter_name=adapter_name,
        policy_id=policy.policy_id,
        metrics=tuple(metrics),
        gates=gates,
        evidence_complete=False,
        release_approved=False,
        warnings=(
            "This is an experimental single-table report, not an anonymity or production claim.",
            "Exact-match diagnostics are necessary but do not replace membership or "
            "attribute inference tests.",
        ),
    )


def _read_stats(path: Path, dataset: DatasetContract) -> _DatasetStats:
    numeric = {
        column.name: [] for column in dataset.columns if column.kind == ColumnKind.CONTINUOUS
    }
    categorical = {
        column.name: Counter() for column in dataset.columns if column.kind == ColumnKind.DISCRETE
    }
    row_hashes: list[str] = []
    invalid = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual_columns = tuple(reader.fieldnames or ())
        header_matches = actual_columns == dataset.column_names
        row_count = 0
        for row in reader:
            row_count += 1
            row_hashes.append(stable_digest(canonical_row(dataset.column_names, row)))
            for column in dataset.columns:
                value = row.get(column.name)
                if value is None or value == "":
                    if not column.nullable:
                        invalid += 1
                    if column.kind == ColumnKind.DISCRETE:
                        categorical[column.name][_NULL_CATEGORY] += 1
                    continue
                if column.kind == ColumnKind.DISCRETE:
                    categorical[column.name][value] += 1
                    continue
                try:
                    parsed = float(value)
                except ValueError:
                    invalid += 1
                    continue
                if not math.isfinite(parsed):
                    invalid += 1
                    continue
                numeric[column.name].append(parsed)
    return _DatasetStats(
        row_count=row_count,
        header_matches=header_matches,
        invalid_value_count=invalid,
        row_hashes=row_hashes,
        numeric=numeric,
        categorical=categorical,
    )


def _read_row_hashes(path: Path, columns: tuple[str, ...]) -> set[str]:
    hashes: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != columns:
            raise ValueError("training CSV columns do not match the reviewed contract")
        for row in reader:
            hashes.add(stable_digest(canonical_row(columns, row)))
    return hashes


def _ks_statistic(left: list[float], right: list[float]) -> float:
    left_sorted = sorted(left)
    right_sorted = sorted(right)
    i = 0
    j = 0
    maximum = 0.0
    while i < len(left_sorted) or j < len(right_sorted):
        if j >= len(right_sorted) or (i < len(left_sorted) and left_sorted[i] <= right_sorted[j]):
            value = left_sorted[i]
        else:
            value = right_sorted[j]
        while i < len(left_sorted) and left_sorted[i] <= value:
            i += 1
        while j < len(right_sorted) and right_sorted[j] <= value:
            j += 1
        maximum = max(maximum, abs(i / len(left_sorted) - j / len(right_sorted)))
    return maximum


def _normalized_mean_error(reference: list[float], generated: list[float]) -> float:
    reference_mean = sum(reference) / len(reference)
    generated_mean = sum(generated) / len(generated)
    variance = sum((value - reference_mean) ** 2 for value in reference) / len(reference)
    scale = max(math.sqrt(variance), abs(reference_mean) * 0.01, 1e-9)
    return abs(generated_mean - reference_mean) / scale


def _total_variation(reference: Counter[str], generated: Counter[str]) -> float:
    reference_total = sum(reference.values())
    generated_total = sum(generated.values())
    if not reference_total or not generated_total:
        return 1.0
    categories = set(reference) | set(generated)
    return 0.5 * sum(
        abs(reference[category] / reference_total - generated[category] / generated_total)
        for category in categories
    )


def _boolean_metric(
    name: str,
    dimension: str,
    value: bool,
    *,
    required: bool = True,
) -> MetricResult:
    status = GateStatus.PASSED if value or not required else GateStatus.FAILED
    return MetricResult(
        name=name,
        dimension=dimension,
        value=value,
        threshold=True if required else None,
        status=status,
    )


def _maximum_metric(
    name: str,
    dimension: str,
    value: float,
    threshold: float,
    column: str | None = None,
) -> MetricResult:
    return MetricResult(
        name=name,
        dimension=dimension,
        value=value,
        threshold=threshold,
        status=GateStatus.PASSED if value <= threshold else GateStatus.FAILED,
        column=column,
    )


def _minimum_metric(
    name: str,
    dimension: str,
    value: float,
    threshold: float,
) -> MetricResult:
    return MetricResult(
        name=name,
        dimension=dimension,
        value=value,
        threshold=threshold,
        status=GateStatus.PASSED if value >= threshold else GateStatus.FAILED,
    )


def _gate(name: str, metrics: list[MetricResult], metric_names: tuple[str, ...]) -> GateResult:
    indexed = {metric.name: metric for metric in metrics}
    selected = [indexed[metric_name] for metric_name in metric_names]
    status = (
        GateStatus.PASSED
        if selected and all(metric.status == GateStatus.PASSED for metric in selected)
        else GateStatus.FAILED
    )
    return GateResult(name=name, status=status, metric_names=metric_names)
