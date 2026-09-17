from __future__ import annotations

import csv
from pathlib import Path

from typer.testing import CliRunner

from databoom.synthesis.cli import app

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
