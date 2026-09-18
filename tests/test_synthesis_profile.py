import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from databoom.synthesis.contracts import (
    ColumnContract,
    ColumnKind,
    DataQualityIntent,
    DataSensitivity,
    DatasetContract,
)
from databoom.synthesis.profiling import (
    create_profile_artifacts,
    profile_csv_dataset,
    verify_profile_artifact,
)


def test_quality_intent_validates_columns_quantiles_and_weights() -> None:
    dataset = _dataset_contract()

    with pytest.raises(ValidationError, match="unknown columns: missing"):
        DataQualityIntent(dataset_contract=dataset, protected_columns=("missing",))
    with pytest.raises(ValidationError, match="quantiles must be unique and sorted"):
        DataQualityIntent(dataset_contract=dataset, quantiles=(0.5, 0.25))
    with pytest.raises(ValidationError, match="column weights"):
        DataQualityIntent(dataset_contract=dataset, column_weights={"x": 1.1})
    with pytest.raises(ValidationError, match="finite number"):
        DataQualityIntent(dataset_contract=dataset, column_weights={"x": float("nan")})


def test_profile_reports_numeric_categorical_missingness_and_dependencies(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.csv"
    _write_rows(
        source,
        [
            ("1", "2", "A", "yes"),
            ("2", "4", "A", "yes"),
            ("3", "6", "B", ""),
            ("4", "8", "B", "no"),
            ("5", "10", "C", "no"),
            ("20", "40", "C", ""),
        ],
    )
    dataset = _dataset_contract()
    intent = DataQualityIntent(
        dataset_contract=dataset,
        sample_row_limit=20,
        histogram_bins=4,
        top_values_limit=2,
    )

    profile = profile_csv_dataset(source, dataset, quality_intent=intent, seed="known")

    assert profile.profile_version == "2"
    assert profile.source_row_count == 6
    assert profile.sampled_row_count == 6
    assert profile.columns[0].numeric is not None
    assert profile.columns[0].numeric.maximum == 20
    assert sum(bucket.count for bucket in profile.columns[0].numeric.histogram) == 6
    assert profile.columns[3].null_count == 2
    assert profile.columns[3].null_rate == pytest.approx(1 / 3)
    assert profile.columns[2].categorical is not None
    assert profile.columns[2].categorical.sampled_distinct_count == 3
    assert len(profile.columns[2].categorical.top_values) == 2
    assert profile.columns[2].categorical.other_count == 2
    assert sum(pattern.count for pattern in profile.missingness_patterns) == 6
    pearson = next(
        dependency
        for dependency in profile.dependencies
        if dependency.left_column == "x"
        and dependency.right_column == "y"
        and dependency.metric == "pearson"
    )
    assert pearson.value == pytest.approx(1.0)
    assert pearson.complete_row_count == 6
    assert {dependency.metric for dependency in profile.dependencies} >= {
        "pearson",
        "correlation_ratio",
        "cramers_v",
    }


def test_profile_sampling_is_deterministic_and_bounded(tmp_path: Path) -> None:
    source = tmp_path / "large.csv"
    _write_rows(
        source,
        [
            (str(index), str(index * 3), f"segment-{index % 9}", "" if index % 4 else "yes")
            for index in range(100)
        ],
    )
    dataset = _dataset_contract()
    intent = DataQualityIntent(
        dataset_contract=dataset,
        sample_row_limit=7,
        column_weights={"x": 0.5, "y": 0.75},
    )
    reordered_intent = DataQualityIntent(
        dataset_contract=dataset,
        sample_row_limit=7,
        column_weights={"y": 0.75, "x": 0.5},
    )

    first = profile_csv_dataset(source, dataset, quality_intent=intent, seed="bounded")
    second = profile_csv_dataset(
        source,
        dataset,
        quality_intent=reordered_intent,
        seed="bounded",
    )

    assert first.profile_id == second.profile_id
    assert first.quality_intent.intent_id == intent.intent_id
    assert first.source_row_count == 100
    assert first.sampled_row_count == 7
    assert first.columns[3].null_count == 75
    assert first.model_dump(exclude={"created_at"}) == second.model_dump(exclude={"created_at"})


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("x,y,segment\n1,2,A\n", "source columns must match"),
        ("x,y,segment,optional\n1,2,A\n", "wrong number of values"),
        ("x,y,segment,optional\n,2,A,yes\n", "null in required column"),
        ("x,y,segment,optional\nnot-a-number,2,A,yes\n", "non-numeric value"),
        ("x,y,segment,optional\ninf,2,A,yes\n", "non-finite value"),
    ],
)
def test_profile_rejects_malformed_or_invalid_source(
    tmp_path: Path,
    body: str,
    message: str,
) -> None:
    source = tmp_path / "invalid.csv"
    source.write_text(body, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        profile_csv_dataset(source, _dataset_contract())


def test_profile_rejects_source_change_during_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.csv"
    _write_rows(
        source,
        [
            ("1", "2", "A", "yes"),
            ("2", "4", "B", ""),
            ("3", "6", "C", "no"),
        ],
    )
    digests = iter(("a" * 64, "b" * 64))
    monkeypatch.setattr(
        "databoom.synthesis.profiling.sha256_file",
        lambda path: next(digests),
    )

    with pytest.raises(ValueError, match="changed while profiling"):
        profile_csv_dataset(source, _dataset_contract())


def test_profile_artifacts_verify_checksum_lineage_and_root(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    _write_rows(
        source,
        [
            ("1", "2", "A", "yes"),
            ("2", "4", "B", ""),
            ("3", "6", "C", "no"),
        ],
    )
    artifact_root = tmp_path / "experiment"
    manifest = create_profile_artifacts(
        source,
        _dataset_contract(),
        artifact_root,
        "profiles/source",
        seed="artifact",
    )

    profile = verify_profile_artifact(manifest, artifact_root)
    assert profile.profile_id == manifest.artifact.profile_id
    payload = json.loads((artifact_root / manifest.artifact.path).read_text())
    assert payload["profile_version"] == "2"

    escaped = manifest.model_copy(
        update={"artifact": manifest.artifact.model_copy(update={"path": "../profile-v2.json"})}
    )
    with pytest.raises(ValueError, match="escapes"):
        verify_profile_artifact(escaped, artifact_root)

    profile_path = artifact_root / manifest.artifact.path
    profile_path.write_text(profile_path.read_text() + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_profile_artifact(manifest, artifact_root)


def test_profile_and_api_import_without_training_libraries() -> None:
    script = """
import sys
import databoom.synthesis.profiling
from databoom.api.app import create_app
from databoom.core.config import Settings
app = create_app(settings=Settings(ENV='test'))
forbidden = {'numpy', 'pandas', 'sklearn', 'tensorflow', 'torch', 'ctgan'}
loaded = sorted(forbidden.intersection(sys.modules))
assert app.title == 'DataBoom API'
assert not loaded, loaded
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def _dataset_contract() -> DatasetContract:
    return DatasetContract(
        name="controlled-profile",
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
            ColumnContract(
                name="segment",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="optional",
                kind=ColumnKind.DISCRETE,
                nullable=True,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )


def _write_rows(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("x", "y", "segment", "optional"))
        writer.writerows(rows)
