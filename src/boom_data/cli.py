"""Command-line entry point for Boom Data."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from boom_data.core.config import get_settings
from boom_data.core.logging import configure_logging
from boom_data.export import ArtifactExporter
from boom_data.generation import DomainProfile, OutputFormat, create_generation_plan
from boom_data.ingest import parse_postgres_ddl
from boom_data.validation import validate_export

app = typer.Typer(
    name="boom-data",
    help="Relationship-aware synthetic data generation for PostgreSQL schemas.",
    no_args_is_help=True,
)


@app.callback()
def main(
    log_level: str | None = typer.Option(
        None,
        "--log-level",
        help="Override BOOM_DATA_LOG_LEVEL for this command.",
    ),
) -> None:
    """Configure shared CLI behavior before command execution."""

    settings = get_settings(log_level=log_level)
    configure_logging(settings.log_level)


@app.command()
def info() -> None:
    """Show the active local Boom Data configuration."""

    settings = get_settings()
    typer.echo(f"environment: {settings.environment}")
    typer.echo(f"artifact_root: {settings.artifact_root}")
    typer.echo(f"database_url: {settings.database_url}")
    typer.echo(f"redis_url: {settings.redis_url}")
    typer.echo(f"log_level: {settings.log_level}")


@app.command()
def generate(
    schema_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            readable=True,
            help="Path to a PostgreSQL DDL schema file.",
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory where generated artifacts should be written.",
        ),
    ] = Path("artifacts/latest"),
    rows: Annotated[
        list[str] | None,
        typer.Option(
            "--rows",
            "-r",
            help="Per-table row count override in table=count form. Repeatable.",
        ),
    ] = None,
    default_row_count: Annotated[
        int,
        typer.Option(
            "--default-row-count",
            min=0,
            help="Default row count for tables without a --rows override.",
        ),
    ] = 10,
    seed: Annotated[
        str,
        typer.Option(
            "--seed",
            help="Deterministic seed used for generation.",
        ),
    ] = "0",
    domain: Annotated[
        DomainProfile,
        typer.Option(
            "--domain",
            help="Semantic domain profile for generated values.",
        ),
    ] = DomainProfile.GENERAL,
    formats: Annotated[
        list[OutputFormat] | None,
        typer.Option(
            "--format",
            help="Output format. Repeat for multiple formats.",
        ),
    ] = None,
) -> None:
    """Generate local synthetic data artifacts from PostgreSQL DDL."""

    database = parse_postgres_ddl(schema_path.read_text(encoding="utf-8"))
    plan = create_generation_plan(
        database,
        row_counts=_parse_row_counts(rows),
        default_row_count=default_row_count,
        seed=seed,
        domain=domain,
        output_formats=tuple(formats or [OutputFormat.CSV]),
    )
    manifest = ArtifactExporter(plan, output_dir).export()
    report = validate_export(plan, manifest)
    validation_path = output_dir / "validation.json"
    report.write_json(validation_path)

    typer.echo(f"tables: {len(plan.tables)}")
    typer.echo(f"rows: {plan.total_rows}")
    typer.echo(f"manifest: {manifest.manifest_path}")
    typer.echo(f"validation: {validation_path}")
    typer.echo(f"passed: {str(report.passed).lower()}")

    if not report.passed:
        raise typer.Exit(code=1)


def _parse_row_counts(values: list[str] | None) -> dict[str, int]:
    row_counts: dict[str, int] = {}
    for value in values or []:
        if "=" not in value:
            raise typer.BadParameter("--rows must use table=count format")
        table_name, raw_count = value.split("=", 1)
        table_name = table_name.strip()
        if not table_name:
            raise typer.BadParameter("--rows table name cannot be empty")
        try:
            row_counts[table_name] = int(raw_count)
        except ValueError as error:
            raise typer.BadParameter("--rows count must be an integer") from error
    return row_counts
