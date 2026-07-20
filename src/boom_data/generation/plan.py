"""Generation plan contracts and builders."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from boom_data.generation.domains import DomainProfile
from boom_data.schema import ColumnSchema, DatabaseSchema, TableSchema, build_relationship_graph
from boom_data.schema.models import TypeFamily


class OutputFormat(StrEnum):
    """Artifact formats supported by the generation plan."""

    CSV = "csv"
    SQL = "sql"


class ColumnStrategy(StrEnum):
    """How the generator should produce a column value."""

    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    DEFAULT = "default"
    GENERATED = "generated"


class PlanModel(BaseModel):
    """Base class for immutable generation plan models."""

    model_config = ConfigDict(frozen=True)


class ForeignKeySource(PlanModel):
    """Source table and columns for a foreign-key column plan."""

    parent_table: str
    child_columns: tuple[str, ...]
    parent_columns: tuple[str, ...]
    constraint_name: str | None = None


class ColumnPlan(PlanModel):
    """Plan for generating a single table column."""

    name: str
    strategy: ColumnStrategy
    type_family: TypeFamily
    nullable: bool
    default: str | None = None
    foreign_key_source: ForeignKeySource | None = None

    @model_validator(mode="after")
    def validate_foreign_key_strategy(self) -> Self:
        if self.strategy == ColumnStrategy.FOREIGN_KEY and self.foreign_key_source is None:
            raise ValueError("foreign-key column plans require a source")
        if self.strategy != ColumnStrategy.FOREIGN_KEY and self.foreign_key_source is not None:
            raise ValueError("only foreign-key column plans can define a source")
        return self


class TablePlan(PlanModel):
    """Plan for generating rows for a table."""

    table_name: str
    row_count: int = Field(ge=0)
    columns: tuple[ColumnPlan, ...]
    dependencies: tuple[str, ...] = Field(default_factory=tuple)

    def column_plan(self, name: str) -> ColumnPlan:
        for column in self.columns:
            if column.name == name:
                return column
        raise KeyError(f"column plan not found: {self.table_name}.{name}")


class GenerationPlan(PlanModel):
    """Full deterministic generation plan for a database schema."""

    seed: int | str
    domain: DomainProfile = DomainProfile.GENERAL
    output_formats: tuple[OutputFormat, ...]
    tables: tuple[TablePlan, ...]

    @field_validator("output_formats")
    @classmethod
    def require_output_formats(cls, value: tuple[OutputFormat, ...]) -> tuple[OutputFormat, ...]:
        if not value:
            raise ValueError("generation plan requires at least one output format")
        return value

    @property
    def total_rows(self) -> int:
        return sum(table.row_count for table in self.tables)

    def table_plan(self, name: str) -> TablePlan:
        for table in self.tables:
            if table.table_name == name or table.table_name.endswith(f".{name}"):
                return table
        raise KeyError(f"table plan not found: {name}")


def create_generation_plan(
    database: DatabaseSchema,
    *,
    row_counts: dict[str, int] | None = None,
    default_row_count: int = 10,
    seed: int | str = 0,
    domain: DomainProfile = DomainProfile.GENERAL,
    output_formats: tuple[OutputFormat, ...] = (OutputFormat.CSV,),
) -> GenerationPlan:
    """Create a deterministic generation plan from schema metadata."""

    if default_row_count < 0:
        raise ValueError("default row count cannot be negative")

    row_counts = row_counts or {}
    _validate_row_count_keys(database, row_counts)

    graph = build_relationship_graph(database)
    table_plans = tuple(
        _build_table_plan(table, graph.parents_for(table), row_counts, default_row_count)
        for table in graph.dependency_order()
    )
    return GenerationPlan(
        seed=seed,
        domain=domain,
        output_formats=output_formats,
        tables=table_plans,
    )


def _build_table_plan(
    table: TableSchema,
    dependencies,
    row_counts: dict[str, int],
    default_row_count: int,
) -> TablePlan:
    foreign_key_columns = {
        column_name: edge
        for edge in dependencies
        for column_name in edge.child_columns
    }
    primary_key_columns = set(table.primary_key.columns if table.primary_key else ())

    return TablePlan(
        table_name=table.qualified_name,
        row_count=_row_count_for(table, row_counts, default_row_count),
        dependencies=tuple(
            edge.parent_table for edge in dependencies if not edge.is_self_reference
        ),
        columns=tuple(
            _build_column_plan(column, primary_key_columns, foreign_key_columns)
            for column in table.columns
        ),
    )


def _build_column_plan(
    column: ColumnSchema,
    primary_key_columns: set[str],
    foreign_key_columns,
) -> ColumnPlan:
    if column.name in primary_key_columns:
        return ColumnPlan(
            name=column.name,
            strategy=ColumnStrategy.PRIMARY_KEY,
            type_family=column.data_type.family,
            nullable=column.nullable,
            default=column.default,
        )
    if column.name in foreign_key_columns:
        edge = foreign_key_columns[column.name]
        return ColumnPlan(
            name=column.name,
            strategy=ColumnStrategy.FOREIGN_KEY,
            type_family=column.data_type.family,
            nullable=column.nullable,
            default=column.default,
            foreign_key_source=ForeignKeySource(
                parent_table=edge.parent_table,
                child_columns=edge.child_columns,
                parent_columns=edge.parent_columns,
                constraint_name=edge.constraint_name,
            ),
        )
    return ColumnPlan(
        name=column.name,
        strategy=ColumnStrategy.DEFAULT if column.default is not None else ColumnStrategy.GENERATED,
        type_family=column.data_type.family,
        nullable=column.nullable,
        default=column.default,
    )


def _row_count_for(table: TableSchema, row_counts: dict[str, int], default_row_count: int) -> int:
    value = row_counts.get(table.qualified_name, row_counts.get(table.name, default_row_count))
    if value < 0:
        raise ValueError(f"row count for {table.qualified_name} cannot be negative")
    return value


def _validate_row_count_keys(database: DatabaseSchema, row_counts: dict[str, int]) -> None:
    qualified = set(database.table_names)
    unqualified = {table.name for table in database.tables}
    unknown = sorted(key for key in row_counts if key not in qualified and key not in unqualified)
    if unknown:
        raise ValueError("row count references unknown tables: " + ", ".join(unknown))
