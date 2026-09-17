from __future__ import annotations

import csv
from pathlib import Path

import pytest
from pydantic import ValidationError

from databoom.synthesis import SplitRatios, SplitRequest
from databoom.synthesis.splitting import (
    load_split_manifest,
    split_csv_dataset,
    verify_split_artifacts,
)


def test_grouped_split_is_deterministic_and_subjects_do_not_cross(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_source(source, row_count=300, rows_per_subject=3)

    first = split_csv_dataset(
        SplitRequest(
            source_path=source,
            output_dir=tmp_path / "first",
            seed="grouped-seed",
            group_columns=("subject_id",),
        )
    )
    second = split_csv_dataset(
        SplitRequest(
            source_path=source,
            output_dir=tmp_path / "second",
            seed="grouped-seed",
            group_columns=("subject_id",),
        )
    )

    assert first.split_id == second.split_id
    assert first.training.sha256 == second.training.sha256
    assert first.validation.sha256 == second.validation.sha256
    assert first.holdout.sha256 == second.holdout.sha256
    assert first.source_row_count == 300

    subject_partitions: dict[str, str] = {}
    for partition in ("training", "validation", "holdout"):
        with (tmp_path / "first" / f"{partition}.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            for row in csv.DictReader(handle):
                previous = subject_partitions.setdefault(row["subject_id"], partition)
                assert previous == partition
    assert len(subject_partitions) == 100

    loaded = load_split_manifest(tmp_path / "first" / "split-manifest.json")
    assert loaded == first
    verify_split_artifacts(loaded, tmp_path / "first" / "split-manifest.json")


def test_split_rejects_invalid_configuration_and_empty_partition(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_source(source, row_count=6, rows_per_subject=1)

    with pytest.raises(ValidationError, match="sum to 1.0"):
        SplitRatios(training=0.5, validation=0.2, holdout=0.2)

    with pytest.raises(ValueError, match="group columns not found"):
        split_csv_dataset(
            SplitRequest(
                source_path=source,
                output_dir=tmp_path / "missing-group",
                seed="0",
                group_columns=("missing",),
            )
        )

    with pytest.raises(ValueError, match="empty partitions"):
        split_csv_dataset(
            SplitRequest(
                source_path=source,
                output_dir=tmp_path / "empty",
                seed="0",
                ratios=SplitRatios(training=0.98, validation=0.01, holdout=0.01),
            )
        )
    assert not (tmp_path / "empty" / "split-manifest.json").exists()


def test_split_checksum_tampering_is_detected(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_source(source, row_count=200, rows_per_subject=1)
    manifest = split_csv_dataset(
        SplitRequest(source_path=source, output_dir=tmp_path / "split", seed="stable")
    )
    training = tmp_path / "split" / manifest.training.path
    training.write_text(training.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_split_artifacts(manifest, tmp_path / "split" / "split-manifest.json")


def _write_source(path: Path, *, row_count: int, rows_per_subject: int) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("subject_id", "age", "segment"),
            lineterminator="\n",
        )
        writer.writeheader()
        for index in range(row_count):
            writer.writerow(
                {
                    "subject_id": f"subject-{index // rows_per_subject:04d}",
                    "age": 20 + index % 50,
                    "segment": ("standard", "premium", "business")[index % 3],
                }
            )
