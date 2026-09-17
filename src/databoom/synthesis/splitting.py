"""Deterministic streaming CSV partitioning for source-trained evaluation."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from pathlib import Path

from databoom.synthesis.contracts import (
    PartitionArtifact,
    SplitManifest,
    SplitRequest,
)
from databoom.synthesis.io import sha256_file, stable_digest, write_model_json

_PARTITION_NAMES = ("training", "validation", "holdout")


def split_csv_dataset(request: SplitRequest) -> SplitManifest:
    """Split a CSV by stable row or subject hashes and write a manifest.

    The source is streamed. Only group-key hashes are retained when grouping is
    requested, which lets the service verify isolation without storing source rows.
    """

    source_path = request.source_path.resolve()
    if not source_path.is_file():
        raise ValueError(f"source CSV does not exist: {source_path}")

    output_dir = request.output_dir.resolve()
    manifest_path = output_dir / "split-manifest.json"
    if manifest_path.exists() and not request.overwrite:
        raise FileExistsError(f"split manifest already exists: {manifest_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    columns, source_row_count, group_count = _inspect_source(source_path, request)
    if source_row_count < 3:
        raise ValueError("source CSV must contain at least three data rows")
    if request.group_columns and group_count < 3:
        raise ValueError("group-preserving splits require at least three distinct groups")

    source_sha256 = sha256_file(source_path)
    split_id = (
        "split_"
        + stable_digest(
            request.algorithm_version,
            source_sha256,
            request.seed,
            request.ratios.model_dump_json(),
            json.dumps(request.group_columns, separators=(",", ":")),
        )[:24]
    )

    final_paths = {name: output_dir / f"{name}.csv" for name in _PARTITION_NAMES}
    temporary_paths = {name: path.with_suffix(".csv.tmp") for name, path in final_paths.items()}
    if not request.overwrite:
        existing = [path for path in final_paths.values() if path.exists()]
        if existing:
            raise FileExistsError(f"partition artifact already exists: {existing[0]}")

    counts = {name: 0 for name in _PARTITION_NAMES}
    group_partitions: dict[str, str] = {}
    try:
        handles = {
            name: path.open("w", encoding="utf-8", newline="")
            for name, path in temporary_paths.items()
        }
        try:
            writers = {
                name: csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
                for name, handle in handles.items()
            }
            for writer in writers.values():
                writer.writeheader()

            with source_path.open("r", encoding="utf-8", newline="") as source:
                reader = csv.DictReader(source)
                for row_index, row in enumerate(reader):
                    unit = _split_unit(row, row_index, request)
                    partition = _partition_for_unit(unit, request)
                    if request.group_columns:
                        previous = group_partitions.setdefault(stable_digest(unit), partition)
                        if previous != partition:
                            raise RuntimeError("group key crossed split partitions")
                    writers[partition].writerow(row)
                    counts[partition] += 1
        finally:
            for handle in handles.values():
                handle.close()

        empty = [name for name, count in counts.items() if count == 0]
        if empty:
            names = ", ".join(empty)
            raise ValueError(f"deterministic split produced empty partitions: {names}")

        for name in _PARTITION_NAMES:
            temporary_paths[name].replace(final_paths[name])
    except Exception:
        for path in temporary_paths.values():
            path.unlink(missing_ok=True)
        raise

    artifacts = {
        name: PartitionArtifact(
            name=name,
            path=final_paths[name].name,
            row_count=counts[name],
            sha256=sha256_file(final_paths[name]),
        )
        for name in _PARTITION_NAMES
    }
    manifest = SplitManifest(
        split_id=split_id,
        source_name=source_path.name,
        source_sha256=source_sha256,
        source_row_count=source_row_count,
        columns=columns,
        algorithm_version=request.algorithm_version,
        strategy=request.strategy,
        seed=request.seed,
        ratios=request.ratios,
        group_columns=request.group_columns,
        training=artifacts["training"],
        validation=artifacts["validation"],
        holdout=artifacts["holdout"],
    )
    write_model_json(manifest_path, manifest)
    return manifest


def load_split_manifest(path: Path) -> SplitManifest:
    """Load a split manifest from JSON."""

    return SplitManifest.model_validate_json(path.read_text(encoding="utf-8"))


def verify_split_artifacts(manifest: SplitManifest, manifest_path: Path) -> None:
    """Verify every partition exists below the manifest root and matches its hash."""

    from databoom.synthesis.io import resolve_within

    root = manifest_path.resolve().parent
    for artifact in (manifest.training, manifest.validation, manifest.holdout):
        path = resolve_within(root, artifact.path)
        if not path.is_file():
            raise ValueError(f"split artifact does not exist: {artifact.path}")
        if sha256_file(path) != artifact.sha256:
            raise ValueError(f"split artifact checksum mismatch: {artifact.path}")


def _inspect_source(source_path: Path, request: SplitRequest) -> tuple[tuple[str, ...], int, int]:
    with source_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        columns = tuple(reader.fieldnames or ())
        if not columns:
            raise ValueError("source CSV must contain a header")
        if len(columns) != len(set(columns)):
            raise ValueError("source CSV header contains duplicate column names")
        missing = [column for column in request.group_columns if column not in columns]
        if missing:
            raise ValueError(f"group columns not found in source CSV: {', '.join(missing)}")

        row_count = 0
        groups: set[str] = set()
        for row_index, row in enumerate(reader):
            row_count += 1
            if request.group_columns:
                groups.add(stable_digest(_split_unit(row, row_index, request)))
    return columns, row_count, len(groups)


def _split_unit(row: Mapping[str, str | None], row_index: int, request: SplitRequest) -> str:
    if not request.group_columns:
        return f"row:{row_index}"
    values = [
        "" if row.get(column) is None else str(row.get(column)) for column in request.group_columns
    ]
    return "group:" + json.dumps(values, ensure_ascii=False, separators=(",", ":"))


def _partition_for_unit(unit: str, request: SplitRequest) -> str:
    digest = stable_digest(request.algorithm_version, request.seed, unit)
    fraction = int(digest[:16], 16) / float(2**64)
    if fraction < request.ratios.training:
        return "training"
    if fraction < request.ratios.training + request.ratios.validation:
        return "validation"
    return "holdout"
