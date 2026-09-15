"""Command-line entry point for DataBoom.

Purpose:
    Provide local developer/operator commands for planning, generating, and
    validating datasets without the web dashboard.

Data flow:
    CLI options -> DDL ingestion -> generation plan -> exporter/validator ->
    terminal summary and artifact files.

Why this layer exists:
    The CLI exercises the same backend engine as the API. That makes local testing,
    benchmarking, and debugging possible without a running frontend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from databoom.core.config import get_settings
from databoom.core.logging import configure_logging
from databoom.export import ArtifactExporter, load_export_manifest
from databoom.generation import (
    DomainProfile,
    GenerationPlan,
    LocaleProfile,
    OutputFormat,
    create_generation_plan,
)
from databoom.ingest import parse_postgres_ddl
from databoom.validation import validate_export

app = typer.Typer(
    name="databoom",
    help="Relationship-aware synthetic data generation for PostgreSQL schemas.",
    no_args_is_help=True,
)


@app.callback()
def main(
    log_level: str | None = typer.Option(
        None,
        "--log-level",
        help="Override DATABOOM_LOG_LEVEL for this command.",
    ),
) -> None:
    """Configure shared CLI behavior before command execution."""

    settings = get_settings(log_level=log_level)
    configure_logging(settings.log_level)


@app.command()
def info() -> None:
    """Show the active local DataBoom configuration."""

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
    locale: Annotated[
        LocaleProfile,
        typer.Option(
            "--locale",
            help="Locale profile for correlated identity and location values.",
        ),
    ] = LocaleProfile.EN_US,
    formats: Annotated[
        list[OutputFormat] | None,
        typer.Option(
            "--format",
            help="Output format. Repeat for multiple formats.",
        ),
    ] = None,
) -> None:
    """Generate local synthetic data artifacts from PostgreSQL DDL."""

    # CLI generation intentionally reuses the same planner/exporter/validator path
    # as API runs so command-line smoke tests catch real backend regressions.
    generation_plan = _build_generation_plan(
        schema_path,
        row_counts=_parse_row_counts(rows),
        default_row_count=default_row_count,
        seed=seed,
        domain=domain,
        locale=locale,
        output_formats=tuple(formats or [OutputFormat.CSV]),
    )
    manifest = ArtifactExporter(generation_plan, output_dir).export()
    report = validate_export(generation_plan, manifest)
    validation_path = output_dir / "validation.json"
    report.write_json(validation_path)

    typer.echo(f"tables: {len(generation_plan.tables)}")
    typer.echo(f"rows: {generation_plan.total_rows}")
    typer.echo(f"manifest: {manifest.manifest_path}")
    typer.echo(f"validation: {validation_path}")
    typer.echo(f"passed: {str(report.passed).lower()}")

    if not report.passed:
        raise typer.Exit(code=1)


@app.command("plan")
def plan_command(
    schema_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            readable=True,
            help="Path to a PostgreSQL DDL schema file.",
        ),
    ],
    output_path: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional path where the JSON plan should be written.",
        ),
    ] = None,
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
    locale: Annotated[
        LocaleProfile,
        typer.Option(
            "--locale",
            help="Locale profile for correlated identity and location values.",
        ),
    ] = LocaleProfile.EN_US,
    formats: Annotated[
        list[OutputFormat] | None,
        typer.Option(
            "--format",
            help="Output format. Repeat for multiple formats.",
        ),
    ] = None,
) -> None:
    """Print or write the deterministic generation plan for a schema."""

    generation_plan = _build_generation_plan(
        schema_path,
        row_counts=_parse_row_counts(rows),
        default_row_count=default_row_count,
        seed=seed,
        domain=domain,
        locale=locale,
        output_formats=tuple(formats or [OutputFormat.CSV]),
    )
    plan_json = generation_plan.model_dump_json(indent=2)

    if output_path is None:
        typer.echo(plan_json)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(plan_json + "\n", encoding="utf-8")
    typer.echo(f"plan: {output_path}")


@app.command("validate")
def validate_command(
    schema_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            readable=True,
            help="Path to the PostgreSQL DDL schema used for generation.",
        ),
    ],
    artifact_dir: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            help="Directory containing manifest.json and generated artifacts.",
        ),
    ],
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
            help="Deterministic seed used for the expected plan.",
        ),
    ] = "0",
    domain: Annotated[
        DomainProfile,
        typer.Option(
            "--domain",
            help="Semantic domain profile for the expected plan.",
        ),
    ] = DomainProfile.GENERAL,
    locale: Annotated[
        LocaleProfile,
        typer.Option(
            "--locale",
            help="Locale profile expected in generated identity and location values.",
        ),
    ] = LocaleProfile.EN_US,
    formats: Annotated[
        list[OutputFormat] | None,
        typer.Option(
            "--format",
            help="Expected output format. Repeat for multiple formats.",
        ),
    ] = None,
) -> None:
    """Validate an existing local artifact directory against a schema and plan."""

    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.exists():
        raise typer.BadParameter(f"manifest not found: {manifest_path}")

    generation_plan = _build_generation_plan(
        schema_path,
        row_counts=_parse_row_counts(rows),
        default_row_count=default_row_count,
        seed=seed,
        domain=domain,
        locale=locale,
        output_formats=tuple(formats or [OutputFormat.CSV]),
    )
    manifest = load_export_manifest(manifest_path)
    report = validate_export(generation_plan, manifest)
    validation_path = artifact_dir / "validation.json"
    report.write_json(validation_path)

    typer.echo(f"tables: {len(generation_plan.tables)}")
    typer.echo(f"rows: {generation_plan.total_rows}")
    typer.echo(f"validation: {validation_path}")
    typer.echo(f"passed: {str(report.passed).lower()}")

    for issue in report.issues:
        typer.echo(f"issue: {issue.code} {issue.table_name or '-'} {issue.message}")

    if not report.passed:
        raise typer.Exit(code=1)


def _build_generation_plan(
    schema_path: Path,
    *,
    row_counts: dict[str, int],
    default_row_count: int,
    seed: str,
    domain: DomainProfile,
    locale: LocaleProfile,
    output_formats: tuple[OutputFormat, ...],
) -> GenerationPlan:
    database = parse_postgres_ddl(schema_path.read_text(encoding="utf-8"))
    return create_generation_plan(
        database,
        row_counts=row_counts,
        default_row_count=default_row_count,
        seed=seed,
        domain=domain,
        locale=locale,
        output_formats=output_formats,
    )


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
