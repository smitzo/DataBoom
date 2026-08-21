"""PostgreSQL source profiling for workspace metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, text

from databoom.api.workspaces import WorkspaceSource


@dataclass(frozen=True)
class TopValue:
    """Frequent value summary for one column."""

    value: str
    count: int


@dataclass(frozen=True)
class ColumnProfile:
    """Observed profile statistics for one column."""

    name: str
    data_type: str
    row_count: int
    null_count: int
    null_rate: float
    distinct_count: int
    min_value: str | None = None
    max_value: str | None = None
    top_values: tuple[TopValue, ...] = ()


@dataclass(frozen=True)
class TableProfile:
    """Observed profile statistics for one source table."""

    name: str
    schema_name: str
    row_count: int
    columns: tuple[ColumnProfile, ...]


@dataclass(frozen=True)
class SourceProfile:
    """Observed profile statistics for one workspace source."""

    source_id: str
    generated_at: datetime
    tables: tuple[TableProfile, ...]

    @property
    def total_rows(self) -> int:
        """Return total profiled rows across all tables."""

        return sum(table.row_count for table in self.tables)


@dataclass(frozen=True)
class ConnectionTest:
    """Result of a live source connection probe."""

    ok: bool
    message: str
    checked_at: datetime


def profile_postgres_source(
    database_url: str,
    source: WorkspaceSource,
    *,
    top_values_limit: int = 5,
) -> SourceProfile:
    """Profile tables and columns from a PostgreSQL workspace source."""

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            table_profiles = tuple(
                _profile_table(connection, resource, top_values_limit=top_values_limit)
                for resource in source.resources
                if resource.resource_type == "table"
            )
    finally:
        engine.dispose()

    return SourceProfile(
        source_id=source.id,
        generated_at=datetime.now(UTC),
        tables=table_profiles,
    )


def test_postgres_connection(database_url: str) -> ConnectionTest:
    """Open a PostgreSQL connection and execute a lightweight readiness query."""

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
    finally:
        engine.dispose()

    return ConnectionTest(
        ok=True,
        message="connection ok",
        checked_at=datetime.now(UTC),
    )


def _profile_table(connection: Any, resource, *, top_values_limit: int) -> TableProfile:
    schema_name = resource.schema_name or "public"
    table_name = _qualified_table(schema_name, resource.name)
    row_count = int(connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())
    columns = tuple(
        _profile_column(
            connection,
            table_name,
            column_name,
            row_count=row_count,
            data_type=_column_type(resource, column_name),
            top_values_limit=top_values_limit,
        )
        for column_name in resource.columns
    )
    return TableProfile(
        name=resource.name,
        schema_name=schema_name,
        row_count=row_count,
        columns=columns,
    )


def _profile_column(
    connection: Any,
    table_name: str,
    column_name: str,
    *,
    row_count: int,
    data_type: str,
    top_values_limit: int,
) -> ColumnProfile:
    column = _sql_identifier(column_name)
    stats = connection.execute(
        text(
            "SELECT "
            f"COUNT(*) FILTER (WHERE {column} IS NULL) AS null_count, "
            f"COUNT(DISTINCT {column}) AS distinct_count, "
            f"MIN({column})::text AS min_value, "
            f"MAX({column})::text AS max_value "
            f"FROM {table_name}"
        )
    ).mappings().one()
    top_values = tuple(
        TopValue(value=str(row["value"]), count=int(row["value_count"]))
        for row in connection.execute(
            text(
                f"SELECT {column}::text AS value, COUNT(*) AS value_count "
                f"FROM {table_name} "
                f"WHERE {column} IS NOT NULL "
                f"GROUP BY {column} "
                "ORDER BY value_count DESC, value ASC "
                f"LIMIT {top_values_limit}"
            )
        ).mappings()
    )
    null_count = int(stats["null_count"])
    return ColumnProfile(
        name=column_name,
        data_type=data_type,
        row_count=row_count,
        null_count=null_count,
        null_rate=round(null_count / row_count, 4) if row_count else 0.0,
        distinct_count=int(stats["distinct_count"]),
        min_value=_optional_string(stats["min_value"]),
        max_value=_optional_string(stats["max_value"]),
        top_values=top_values,
    )


def _column_type(resource, column_name: str) -> str:
    for column in resource.column_details:
        if column.name == column_name:
            return column.data_type
    return ""


def _qualified_table(schema_name: str, table_name: str) -> str:
    return f"{_sql_identifier(schema_name)}.{_sql_identifier(table_name)}"


def _sql_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
