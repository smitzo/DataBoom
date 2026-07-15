"""Command-line entry point for Boom Data."""

from __future__ import annotations

import typer

from boom_data.core.config import get_settings
from boom_data.core.logging import configure_logging

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
