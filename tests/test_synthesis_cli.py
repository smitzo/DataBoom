from __future__ import annotations

import csv
from pathlib import Path

from typer.testing import CliRunner

from databoom.synthesis.cli import app
from databoom.synthesis.contracts import (
    ColumnContract,
    ColumnKind,
    DataSensitivity,
    DatasetContract,
)

runner = CliRunner()


def test_capabilities_command_works_without_neural_extra() -> None:
    result = runner.invoke(app, ["capabilities"])

    assert result.exit_code == 0
    assert '"name": "empirical-independent"' in result.stdout
    assert '"name": "ctgan"' in result.stdout
    assert '"name": "sklearn-gaussian-mixture"' in result.stdout
    assert '"name": "tensorflow-gan"' in result.stdout


def test_split_command_writes_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("subject", "value"), lineterminator="\n")
        writer.writeheader()
        for index in range(200):
            writer.writerow({"subject": f"s-{index // 2}", "value": index})

    result = runner.invoke(
        app,
        [
            "split",
            str(source),
            "--output-dir",
            str(tmp_path / "split"),
            "--seed",
            "cli-seed",
            "--group-column",
            "subject",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "training_rows:" in result.stdout
    assert (tmp_path / "split" / "split-manifest.json").is_file()


def test_profile_command_writes_verified_profile_v2(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("amount,status\n10,paid\n20,pending\n30,paid\n", encoding="utf-8")
    contract = DatasetContract(
        name="payments",
        columns=(
            ColumnContract(
                name="amount",
                kind=ColumnKind.CONTINUOUS,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
            ColumnContract(
                name="status",
                kind=ColumnKind.DISCRETE,
                sensitivity=DataSensitivity.NON_SENSITIVE,
            ),
        ),
    )
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(contract.model_dump_json(indent=2), encoding="utf-8")
    output_dir = tmp_path / "profile"

    result = runner.invoke(
        app,
        [
            "profile",
            str(source),
            str(contract_path),
            "--output-dir",
            str(output_dir),
            "--sample-row-limit",
            "3",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "source_rows: 3" in result.stdout
    assert "sampled_rows: 3" in result.stdout
    assert (output_dir / "profile-v2.json").is_file()
    assert (output_dir / "profile-manifest.json").is_file()
