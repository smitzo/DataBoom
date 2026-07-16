from typer.testing import CliRunner

from boom_data.cli import app


def test_cli_generate_writes_artifacts(tmp_path) -> None:
    schema_path = tmp_path / "schema.sql"
    output_dir = tmp_path / "out"
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


def test_cli_generate_rejects_invalid_row_override(tmp_path) -> None:
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text("CREATE TABLE users (id bigint PRIMARY KEY);", encoding="utf-8")

    result = CliRunner().invoke(app, ["generate", str(schema_path), "--rows", "users"])

    assert result.exit_code != 0
    assert "--rows must use table=count format" in result.output
