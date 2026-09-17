"""Deterministic, bounded-memory statistical Profile v2 computation."""

from __future__ import annotations

import csv
import heapq
import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from databoom.synthesis.contracts import (
    CategoricalProfile,
    CategoryFrequency,
    ColumnKind,
    ColumnStatisticalProfile,
    DataQualityIntent,
    DatasetContract,
    DependencyProfile,
    HistogramBin,
    MissingnessPattern,
    NumericProfile,
    ProfileArtifact,
    ProfileManifest,
    QuantileValue,
    StatisticalProfile,
)
from databoom.synthesis.io import (
    canonical_row,
    relative_to_root,
    resolve_within,
    sha256_file,
    stable_digest,
    write_model_json,
)

type ProfileValue = float | str | None
type ProfileRow = dict[str, ProfileValue]

SAMPLING_ALGORITHM = "hash-priority-v1"


def _canonical_model_json(model: DatasetContract | DataQualityIntent) -> str:
    return json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def profile_csv_dataset(
    source_path: Path,
    dataset_contract: DatasetContract,
    *,
    quality_intent: DataQualityIntent | None = None,
    seed: str = "profile-0",
) -> StatisticalProfile:
    """Build Profile v2 evidence while retaining at most the configured rows."""

    if not seed:
        raise ValueError("profile seed cannot be empty")
    dataset_contract.require_training_eligible()
    intent = quality_intent or DataQualityIntent(dataset_contract=dataset_contract)
    if intent.dataset_contract != dataset_contract:
        raise ValueError("quality intent dataset contract must match profiled dataset")

    source = source_path.resolve()
    source_sha256 = sha256_file(source)
    columns = dataset_contract.column_names
    null_counts = {column: 0 for column in columns}
    sample_heap: list[tuple[int, int, ProfileRow]] = []
    row_count = 0

    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("source CSV is missing a header")
        if tuple(reader.fieldnames) != columns:
            raise ValueError(
                "source columns must match the reviewed dataset contract: "
                f"expected {list(columns)}, got {reader.fieldnames}"
            )
        contract_by_name = {column.name: column for column in dataset_contract.columns}
        for row_number, raw_row in enumerate(reader, start=2):
            if None in raw_row or any(raw_row[column] is None for column in columns):
                raise ValueError(f"source CSV row {row_number} has the wrong number of values")
            normalized = _normalize_row(raw_row, contract_by_name, row_number=row_number)
            row_count += 1
            for column in columns:
                if normalized[column] is None:
                    null_counts[column] += 1
            _retain_sample_row(
                sample_heap,
                normalized,
                columns=columns,
                seed=seed,
                row_index=row_count - 1,
                limit=intent.sample_row_limit,
            )

    if sha256_file(source) != source_sha256:
        raise ValueError("source CSV changed while profiling")

    sampled_rows = [entry[2] for entry in sorted(sample_heap, reverse=True)]
    warnings: list[str] = []
    column_profiles = tuple(
        _profile_column(
            column.name,
            column.kind,
            sampled_rows,
            row_count=row_count,
            null_count=null_counts[column.name],
            intent=intent,
            warnings=warnings,
        )
        for column in dataset_contract.columns
    )
    missingness_patterns = _missingness_patterns(sampled_rows, columns, intent)
    dependencies = _dependency_profiles(
        sampled_rows,
        dataset_contract,
        warnings=warnings,
    )
    profile_id = "profile_" + stable_digest(
        source_sha256,
        _canonical_model_json(dataset_contract),
        _canonical_model_json(intent),
        seed,
        SAMPLING_ALGORITHM,
    )[:24]
    if not row_count:
        warnings.append("source CSV contains no data rows")

    return StatisticalProfile(
        profile_id=profile_id,
        source_name=source.name,
        source_sha256=source_sha256,
        source_row_count=row_count,
        sampled_row_count=len(sampled_rows),
        sample_row_limit=intent.sample_row_limit,
        sampling_algorithm=SAMPLING_ALGORITHM,
        sampling_seed=seed,
        dataset_contract=dataset_contract,
        quality_intent=intent,
        columns=column_profiles,
        missingness_patterns=missingness_patterns,
        dependencies=dependencies,
        warnings=tuple(sorted(set(warnings))),
    )


def write_profile_artifacts(
    profile: StatisticalProfile,
    artifact_root: Path,
    relative_directory: str,
    *,
    overwrite: bool = False,
) -> ProfileManifest:
    """Write a Profile v2 JSON document and its integrity manifest."""

    root = artifact_root.resolve()
    profile_path = resolve_within(root, f"{relative_directory}/profile-v2.json")
    manifest_path = resolve_within(root, f"{relative_directory}/profile-manifest.json")
    existing = [path for path in (profile_path, manifest_path) if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(f"profile artifact already exists: {existing[0]}")
    write_model_json(profile_path, profile)
    artifact = ProfileArtifact(
        path=relative_to_root(root, profile_path),
        profile_id=profile.profile_id,
        source_row_count=profile.source_row_count,
        sampled_row_count=profile.sampled_row_count,
        sha256=sha256_file(profile_path),
    )
    manifest = ProfileManifest(artifact=artifact)
    write_model_json(manifest_path, manifest)
    return manifest


def create_profile_artifacts(
    source_path: Path,
    dataset_contract: DatasetContract,
    artifact_root: Path,
    relative_directory: str,
    *,
    quality_intent: DataQualityIntent | None = None,
    seed: str = "profile-0",
    overwrite: bool = False,
) -> ProfileManifest:
    """Compute and persist one checksummed Profile v2 artifact."""

    profile = profile_csv_dataset(
        source_path,
        dataset_contract,
        quality_intent=quality_intent,
        seed=seed,
    )
    return write_profile_artifacts(
        profile,
        artifact_root,
        relative_directory,
        overwrite=overwrite,
    )


def load_profile_manifest(path: Path) -> ProfileManifest:
    """Load one Profile v2 manifest from JSON."""

    return ProfileManifest.model_validate_json(path.read_text(encoding="utf-8"))


def verify_profile_artifact(
    manifest: ProfileManifest,
    artifact_root: Path,
) -> StatisticalProfile:
    """Verify path containment, checksum, lineage, and Profile v2 structure."""

    path = resolve_within(artifact_root, manifest.artifact.path)
    if sha256_file(path) != manifest.artifact.sha256:
        raise ValueError("profile artifact checksum mismatch")
    profile = StatisticalProfile.model_validate_json(path.read_text(encoding="utf-8"))
    if profile.profile_id != manifest.artifact.profile_id:
        raise ValueError("profile artifact identifier mismatch")
    if profile.source_row_count != manifest.artifact.source_row_count:
        raise ValueError("profile artifact source row count mismatch")
    if profile.sampled_row_count != manifest.artifact.sampled_row_count:
        raise ValueError("profile artifact sampled row count mismatch")
    return profile


def _normalize_row(
    raw_row: dict[str | None, str | list[str] | None],
    contract_by_name: dict[str, Any],
    *,
    row_number: int,
) -> ProfileRow:
    normalized: ProfileRow = {}
    for name, contract in contract_by_name.items():
        raw_value = raw_row[name]
        if not isinstance(raw_value, str):
            raise ValueError(f"source CSV row {row_number} has an invalid {name!r} value")
        if raw_value == "":
            if not contract.nullable:
                raise ValueError(
                    f"source CSV row {row_number} has null in required column {name!r}"
                )
            normalized[name] = None
            continue
        if contract.kind == ColumnKind.CONTINUOUS:
            try:
                value = float(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"source CSV row {row_number} has non-numeric value in {name!r}"
                ) from exc
            if not math.isfinite(value):
                raise ValueError(
                    f"source CSV row {row_number} has non-finite value in {name!r}"
                )
            normalized[name] = value
        else:
            normalized[name] = raw_value
    return normalized


def _retain_sample_row(
    sample_heap: list[tuple[int, int, ProfileRow]],
    row: ProfileRow,
    *,
    columns: tuple[str, ...],
    seed: str,
    row_index: int,
    limit: int,
) -> None:
    priority = int(stable_digest(seed, str(row_index), canonical_row(columns, row)), 16)
    entry = (-priority, -row_index, row)
    if len(sample_heap) < limit:
        heapq.heappush(sample_heap, entry)
    elif entry > sample_heap[0]:
        heapq.heapreplace(sample_heap, entry)


def _profile_column(
    name: str,
    kind: ColumnKind,
    sampled_rows: list[ProfileRow],
    *,
    row_count: int,
    null_count: int,
    intent: DataQualityIntent,
    warnings: list[str],
) -> ColumnStatisticalProfile:
    values = [row[name] for row in sampled_rows if row[name] is not None]
    common = {
        "name": name,
        "kind": kind,
        "row_count": row_count,
        "null_count": null_count,
        "null_rate": null_count / row_count if row_count else 0.0,
        "sampled_non_null_count": len(values),
    }
    if kind == ColumnKind.CONTINUOUS:
        numeric = _numeric_profile(name, [float(value) for value in values], intent, warnings)
        return ColumnStatisticalProfile(**common, numeric=numeric)
    categorical = _categorical_profile([str(value) for value in values], intent)
    return ColumnStatisticalProfile(**common, categorical=categorical)


def _numeric_profile(
    name: str,
    values: list[float],
    intent: DataQualityIntent,
    warnings: list[str],
) -> NumericProfile | None:
    if not values:
        warnings.append(f"continuous column {name!r} has no sampled non-null values")
        return None
    ordered = sorted(values)
    mean = math.fsum(ordered) / len(ordered)
    variance = math.fsum((value - mean) ** 2 for value in ordered) / len(ordered)
    standard_deviation = math.sqrt(variance)
    skewness = None
    if len(ordered) >= 3 and standard_deviation > 0:
        skewness = (
            math.fsum((value - mean) ** 3 for value in ordered)
            / len(ordered)
            / standard_deviation**3
        )
    elif len(ordered) < 3:
        warnings.append(f"continuous column {name!r} has fewer than three sampled values")
    quantiles = tuple(
        QuantileValue(probability=probability, value=_quantile(ordered, probability))
        for probability in intent.quantiles
    )
    lower_quartile = _quantile(ordered, 0.25)
    upper_quartile = _quantile(ordered, 0.75)
    interquartile_range = upper_quartile - lower_quartile
    lower_fence = lower_quartile - 1.5 * interquartile_range
    upper_fence = upper_quartile + 1.5 * interquartile_range
    return NumericProfile(
        minimum=ordered[0],
        maximum=ordered[-1],
        mean=mean,
        standard_deviation=standard_deviation,
        skewness=skewness,
        quantiles=quantiles,
        histogram=_histogram(ordered, intent.histogram_bins),
        lower_tail_rate=sum(value < lower_fence for value in ordered) / len(ordered),
        upper_tail_rate=sum(value > upper_fence for value in ordered) / len(ordered),
    )


def _categorical_profile(
    values: list[str],
    intent: DataQualityIntent,
) -> CategoricalProfile:
    counts = Counter(values)
    ordered_counts = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top_counts = ordered_counts[: intent.top_values_limit]
    top_total = sum(count for _, count in top_counts)
    total = len(values)
    return CategoricalProfile(
        sampled_distinct_count=len(counts),
        top_values=tuple(
            CategoryFrequency(value=value, count=count, rate=count / total)
            for value, count in top_counts
        ),
        other_count=total - top_total,
        top_values_coverage=top_total / total if total else 0.0,
    )


def _quantile(ordered: list[float], probability: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]
    fraction = position - lower_index
    return ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction


def _histogram(ordered: list[float], bin_count: int) -> tuple[HistogramBin, ...]:
    minimum = ordered[0]
    maximum = ordered[-1]
    if minimum == maximum:
        return (HistogramBin(lower_bound=minimum, upper_bound=maximum, count=len(ordered)),)
    width = (maximum - minimum) / bin_count
    counts = [0] * bin_count
    for value in ordered:
        index = min(int((value - minimum) / width), bin_count - 1)
        counts[index] += 1
    return tuple(
        HistogramBin(
            lower_bound=minimum + index * width,
            upper_bound=maximum if index == bin_count - 1 else minimum + (index + 1) * width,
            count=count,
        )
        for index, count in enumerate(counts)
    )


def _missingness_patterns(
    rows: list[ProfileRow],
    columns: tuple[str, ...],
    intent: DataQualityIntent,
) -> tuple[MissingnessPattern, ...]:
    if not rows:
        return ()
    counts = Counter(tuple(column for column in columns if row[column] is None) for row in rows)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return tuple(
        MissingnessPattern(columns=pattern, count=count, rate=count / len(rows))
        for pattern, count in ordered[: intent.missingness_patterns_limit]
    )


def _dependency_profiles(
    rows: list[ProfileRow],
    dataset_contract: DatasetContract,
    *,
    warnings: list[str],
) -> tuple[DependencyProfile, ...]:
    dependencies: list[DependencyProfile] = []
    for left, right in combinations(dataset_contract.columns, 2):
        complete = [
            (row[left.name], row[right.name])
            for row in rows
            if row[left.name] is not None and row[right.name] is not None
        ]
        metric = _value_dependency_metric(left.kind, right.kind)
        value = _dependency_value(complete, left.kind, right.kind)
        if value is None:
            warnings.append(
                f"dependency {metric} is undefined for {left.name!r} and {right.name!r}"
            )
        else:
            dependencies.append(
                DependencyProfile(
                    left_column=left.name,
                    right_column=right.name,
                    metric=metric,
                    value=value,
                    complete_row_count=len(complete),
                )
            )
        missing_pairs = [
            (row[left.name] is None, row[right.name] is None) for row in rows
        ]
        missingness_phi = _pearson(
            [
                (float(left_missing), float(right_missing))
                for left_missing, right_missing in missing_pairs
            ]
        )
        if missingness_phi is not None:
            dependencies.append(
                DependencyProfile(
                    left_column=left.name,
                    right_column=right.name,
                    metric="missingness_phi",
                    value=missingness_phi,
                    complete_row_count=len(missing_pairs),
                )
            )
    return tuple(dependencies)


def _value_dependency_metric(left: ColumnKind, right: ColumnKind) -> str:
    if left == ColumnKind.CONTINUOUS and right == ColumnKind.CONTINUOUS:
        return "pearson"
    if left == ColumnKind.DISCRETE and right == ColumnKind.DISCRETE:
        return "cramers_v"
    return "correlation_ratio"


def _dependency_value(
    pairs: list[tuple[ProfileValue, ProfileValue]],
    left: ColumnKind,
    right: ColumnKind,
) -> float | None:
    if left == ColumnKind.CONTINUOUS and right == ColumnKind.CONTINUOUS:
        return _pearson([(float(x), float(y)) for x, y in pairs])
    if left == ColumnKind.DISCRETE and right == ColumnKind.DISCRETE:
        return _cramers_v([(str(x), str(y)) for x, y in pairs])
    if left == ColumnKind.DISCRETE:
        return _correlation_ratio([(str(x), float(y)) for x, y in pairs])
    return _correlation_ratio([(str(y), float(x)) for x, y in pairs])


def _pearson(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    mean_x = math.fsum(x for x, _ in pairs) / len(pairs)
    mean_y = math.fsum(y for _, y in pairs) / len(pairs)
    sum_xx = math.fsum((x - mean_x) ** 2 for x, _ in pairs)
    sum_yy = math.fsum((y - mean_y) ** 2 for _, y in pairs)
    if sum_xx == 0 or sum_yy == 0:
        return None
    value = math.fsum((x - mean_x) * (y - mean_y) for x, y in pairs) / math.sqrt(
        sum_xx * sum_yy
    )
    return max(-1.0, min(1.0, value))


def _cramers_v(pairs: list[tuple[str, str]]) -> float | None:
    if len(pairs) < 2:
        return None
    table = Counter(pairs)
    row_counts = Counter(left for left, _ in pairs)
    column_counts = Counter(right for _, right in pairs)
    denominator = min(len(row_counts) - 1, len(column_counts) - 1)
    if denominator <= 0:
        return None
    total = len(pairs)
    chi_squared = 0.0
    for left in row_counts:
        for right in column_counts:
            expected = row_counts[left] * column_counts[right] / total
            observed = table[(left, right)]
            chi_squared += (observed - expected) ** 2 / expected
    return min(1.0, math.sqrt((chi_squared / total) / denominator))


def _correlation_ratio(pairs: list[tuple[str, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    grouped: dict[str, list[float]] = defaultdict(list)
    for category, value in pairs:
        grouped[category].append(value)
    if len(grouped) < 2:
        return None
    mean = math.fsum(value for _, value in pairs) / len(pairs)
    total_variation = math.fsum((value - mean) ** 2 for _, value in pairs)
    if total_variation == 0:
        return None
    between_variation = math.fsum(
        len(values) * ((math.fsum(values) / len(values)) - mean) ** 2
        for values in grouped.values()
    )
    return min(1.0, math.sqrt(between_variation / total_variation))
