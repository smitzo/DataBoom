"""PostgreSQL source profiling for workspace metadata.

Purpose:
    Measure source-table statistics that can later guide synthetic generation.

Data flow:
    live PostgreSQL source -> table/column/relationship stats -> `SourceProfile`
    snapshot -> state store -> generation-plan hints.

Why this layer exists:
    Schema tells us what can be generated; profiling tells us what the source looks
    like. Keeping profiling separate from generation lets DataBoom support other
    source systems later without rewriting the row engine.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
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
class ChildCountFrequency:
    """How many parent keys have a specific number of child rows."""

    child_count: int
    parent_frequency: int


@dataclass(frozen=True)
class RelationshipProfile:
    """Observed fanout statistics for one source foreign-key relationship."""

    child_table: str
    child_schema: str
    child_columns: tuple[str, ...]
    parent_table: str
    parent_schema: str
    parent_columns: tuple[str, ...]
    parent_key_count: int
    child_row_count: int
    distinct_parent_keys_referenced: int
    min_children_per_parent: int
    max_children_per_parent: int
    average_children_per_parent: float
    empty_parent_count: int
    child_count_frequencies: tuple[ChildCountFrequency, ...] = ()


@dataclass(frozen=True)
class SourceProfile:
    """Observed profile statistics for one workspace source.

    Profiles are snapshots, not live dependencies. A run can use the latest cached
    profile even when generation itself only writes local artifacts.
    """

    source_id: str
    generated_at: datetime
    tables: tuple[TableProfile, ...]
    relationships: tuple[RelationshipProfile, ...] = ()

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
    """Profile tables, columns, and relationships from a PostgreSQL source."""

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            table_profiles = tuple(
                _profile_table(connection, resource, top_values_limit=top_values_limit)
                for resource in source.resources
                if resource.resource_type == "table"
            )
            relationship_profiles = tuple(
                _profile_relationship(connection, resource, foreign_key)
                for resource in source.resources
                if resource.resource_type == "table"
                for foreign_key in resource.foreign_keys
            )
    finally:
        engine.dispose()

    return SourceProfile(
        source_id=source.id,
        generated_at=datetime.now(UTC),
        tables=table_profiles,
        relationships=relationship_profiles,
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


def source_profile_to_payload(profile: SourceProfile) -> dict[str, Any]:
    """Serialize a source profile snapshot into JSON-compatible storage."""

    return {
        "source_id": profile.source_id,
        "generated_at": profile.generated_at.isoformat(),
        "total_rows": profile.total_rows,
        "tables": [
            {
                "name": table.name,
                "schema_name": table.schema_name,
                "row_count": table.row_count,
                "columns": [
                    {
                        "name": column.name,
                        "data_type": column.data_type,
                        "row_count": column.row_count,
                        "null_count": column.null_count,
                        "null_rate": column.null_rate,
                        "distinct_count": column.distinct_count,
                        "min_value": column.min_value,
                        "max_value": column.max_value,
                        "top_values": [
                            {"value": top_value.value, "count": top_value.count}
                            for top_value in column.top_values
                        ],
                    }
                    for column in table.columns
                ],
            }
            for table in profile.tables
        ],
        "relationships": [
            {
                "child_table": relationship.child_table,
                "child_schema": relationship.child_schema,
                "child_columns": list(relationship.child_columns),
                "parent_table": relationship.parent_table,
                "parent_schema": relationship.parent_schema,
                "parent_columns": list(relationship.parent_columns),
                "parent_key_count": relationship.parent_key_count,
                "child_row_count": relationship.child_row_count,
                "distinct_parent_keys_referenced": (
                    relationship.distinct_parent_keys_referenced
                ),
                "min_children_per_parent": relationship.min_children_per_parent,
                "max_children_per_parent": relationship.max_children_per_parent,
                "average_children_per_parent": relationship.average_children_per_parent,
                "empty_parent_count": relationship.empty_parent_count,
                "child_count_frequencies": [
                    {
                        "child_count": frequency.child_count,
                        "parent_frequency": frequency.parent_frequency,
                    }
                    for frequency in relationship.child_count_frequencies
                ],
            }
            for relationship in profile.relationships
        ],
    }


def source_profile_from_payload(payload: Mapping[str, Any]) -> SourceProfile:
    """Hydrate a source profile snapshot from JSON-compatible storage."""

    generated_at = payload["generated_at"]
    if isinstance(generated_at, str):
        generated_at = datetime.fromisoformat(generated_at)

    return SourceProfile(
        source_id=str(payload["source_id"]),
        generated_at=generated_at,
        tables=tuple(
            TableProfile(
                name=str(table["name"]),
                schema_name=str(table["schema_name"]),
                row_count=int(table["row_count"]),
                columns=tuple(
                    ColumnProfile(
                        name=str(column["name"]),
                        data_type=str(column["data_type"]),
                        row_count=int(column["row_count"]),
                        null_count=int(column["null_count"]),
                        null_rate=float(column["null_rate"]),
                        distinct_count=int(column["distinct_count"]),
                        min_value=_optional_string(column.get("min_value")),
                        max_value=_optional_string(column.get("max_value")),
                        top_values=tuple(
                            TopValue(value=str(value["value"]), count=int(value["count"]))
                            for value in column.get("top_values", ())
                        ),
                    )
                    for column in table.get("columns", ())
                ),
            )
            for table in payload.get("tables", ())
        ),
        relationships=tuple(
            RelationshipProfile(
                child_table=str(relationship["child_table"]),
                child_schema=str(relationship["child_schema"]),
                child_columns=tuple(relationship["child_columns"]),
                parent_table=str(relationship["parent_table"]),
                parent_schema=str(relationship["parent_schema"]),
                parent_columns=tuple(relationship["parent_columns"]),
                parent_key_count=int(relationship["parent_key_count"]),
                child_row_count=int(relationship["child_row_count"]),
                distinct_parent_keys_referenced=int(
                    relationship["distinct_parent_keys_referenced"]
                ),
                min_children_per_parent=int(relationship["min_children_per_parent"]),
                max_children_per_parent=int(relationship["max_children_per_parent"]),
                average_children_per_parent=float(
                    relationship["average_children_per_parent"]
                ),
                empty_parent_count=int(relationship["empty_parent_count"]),
                child_count_frequencies=tuple(
                    ChildCountFrequency(
                        child_count=int(frequency["child_count"]),
                        parent_frequency=int(frequency["parent_frequency"]),
                    )
                    for frequency in relationship.get("child_count_frequencies", ())
                ),
            )
            for relationship in payload.get("relationships", ())
        ),
    )


def _profile_table(connection: Any, resource, *, top_values_limit: int) -> TableProfile:
    """Collect row count and column profiles for one workspace table resource."""

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
    """Collect null, distinct, min/max, and top-value stats for one column."""

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
    # Top values are stored as strings because the profile contract must survive
    # JSON storage and later feed multiple type-specific generators.
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


def _profile_relationship(connection: Any, resource, foreign_key) -> RelationshipProfile:
    """Collect parent-child fanout stats for one foreign-key relationship."""

    child_schema = resource.schema_name or "public"
    parent_schema = foreign_key.referred_schema or "public"
    child_table = _qualified_table(child_schema, resource.name)
    parent_table = _qualified_table(parent_schema, foreign_key.referred_table)
    child_columns = tuple(_sql_identifier(column) for column in foreign_key.columns)
    parent_key_count = int(
        connection.execute(text(f"SELECT COUNT(*) FROM {parent_table}")).scalar_one()
    )
    where_clause = " AND ".join(f"{column} IS NOT NULL" for column in child_columns)
    grouped_counts = [
        int(row["child_count"])
        for row in connection.execute(
            text(
                "SELECT "
                f"{', '.join(child_columns)}, "
                "COUNT(*) AS child_count "
                f"FROM {child_table} "
                f"WHERE {where_clause} "
                f"GROUP BY {', '.join(child_columns)}"
            )
        ).mappings()
    ]
    child_row_count = sum(grouped_counts)
    distinct_parent_keys_referenced = len(grouped_counts)
    empty_parent_count = max(0, parent_key_count - distinct_parent_keys_referenced)
    min_children = min(grouped_counts) if grouped_counts and empty_parent_count == 0 else 0
    max_children = max(grouped_counts) if grouped_counts else 0
    child_count_frequency = Counter(grouped_counts)
    if empty_parent_count:
        # Empty parents are part of the source distribution. Preserving them lets
        # profile-driven fanout avoid forcing every parent to have a child row.
        child_count_frequency[0] += empty_parent_count

    return RelationshipProfile(
        child_table=resource.name,
        child_schema=child_schema,
        child_columns=foreign_key.columns,
        parent_table=foreign_key.referred_table,
        parent_schema=parent_schema,
        parent_columns=foreign_key.referred_columns,
        parent_key_count=parent_key_count,
        child_row_count=child_row_count,
        distinct_parent_keys_referenced=distinct_parent_keys_referenced,
        min_children_per_parent=min_children,
        max_children_per_parent=max_children,
        average_children_per_parent=(
            child_row_count / parent_key_count if parent_key_count else 0.0
        ),
        empty_parent_count=empty_parent_count,
        child_count_frequencies=tuple(
            ChildCountFrequency(child_count=count, parent_frequency=frequency)
            for count, frequency in sorted(child_count_frequency.items())
        ),
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
