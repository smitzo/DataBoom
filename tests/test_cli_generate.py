import json
from pathlib import Path

from typer.testing import CliRunner

from boom_data.cli import app


def _write_schema(tmp_path: Path) -> Path:
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text(
        """
        CREATE TABLE accounts (id bigint PRIMARY KEY, name text NOT NULL);
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint REFERENCES accounts(id),
            email text NOT NULL
        );
        """,
        encoding="utf-8",
    )
    return schema_path


def test_cli_generate_writes_artifacts(tmp_path) -> None:
    schema_path = _write_schema(tmp_path)
    output_dir = tmp_path / "out"

    result = CliRunner().invoke(
        app,
        [
            "generate",
            str(schema_path),
            "--output-dir",
            str(output_dir),
            "--rows",
            "accounts=2",
            "--rows",
            "users=3",
            "--format",
            "csv",
            "--format",
            "sql",
            "--seed",
            "demo",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "passed: true" in result.output
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "validation.json").exists()
    assert (output_dir / "public__users.csv").exists()
    assert (output_dir / "public__users.sql").exists()


def test_cli_plan_prints_generation_plan(tmp_path) -> None:
    schema_path = _write_schema(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "plan",
            str(schema_path),
            "--rows",
            "accounts=2",
            "--rows",
            "users=3",
            "--format",
            "csv",
            "--seed",
            "demo",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["seed"] == "demo"
    assert [table["table_name"] for table in payload["tables"]] == [
        "public.accounts",
        "public.users",
    ]
    assert [table["row_count"] for table in payload["tables"]] == [2, 3]


def test_cli_validate_existing_artifacts(tmp_path) -> None:
    schema_path = _write_schema(tmp_path)
    output_dir = tmp_path / "out"
    runner = CliRunner()

    generate_result = runner.invoke(
        app,
        [
            "generate",
            str(schema_path),
            "--output-dir",
            str(output_dir),
            "--rows",
            "accounts=2",
            "--rows",
            "users=3",
            "--format",
            "csv",
            "--format",
            "sql",
        ],
    )
    validate_result = runner.invoke(
        app,
        [
            "validate",
            str(schema_path),
            str(output_dir),
            "--rows",
            "accounts=2",
            "--rows",
            "users=3",
            "--format",
            "csv",
            "--format",
            "sql",
        ],
    )

    assert generate_result.exit_code == 0, generate_result.output
    assert validate_result.exit_code == 0, validate_result.output
    assert "passed: true" in validate_result.output


def test_cli_generate_rejects_invalid_row_override(tmp_path) -> None:
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text("CREATE TABLE users (id bigint PRIMARY KEY);", encoding="utf-8")

    result = CliRunner().invoke(app, ["generate", str(schema_path), "--rows", "users"])

    assert result.exit_code != 0
    assert "--rows must use table=count format" in result.output
