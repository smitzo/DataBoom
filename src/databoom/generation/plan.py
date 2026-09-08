"""Generation plan contracts and builders.

Purpose:
    Convert normalized source schema metadata into an immutable execution plan.

Data flow:
    `DatabaseSchema` -> relationship graph -> table dependency order -> `TablePlan`
    objects -> `ColumnPlan` objects with key/default/profile strategies attached.

Why this layer exists:
    Generation should not repeatedly inspect raw DDL, SQLAlchemy metadata, or
    workspace payloads while rows are being written. The planner centralizes those
    decisions once, so the row engine can stay fast and deterministic.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from databoom.generation.domains import DomainProfile
from databoom.schema import ColumnSchema, DatabaseSchema, TableSchema, build_relationship_graph
from databoom.schema.models import TypeFamily


class OutputFormat(StrEnum):
    """Artifact formats supported by the generation plan."""

    CSV = "csv"
    JSON = "json"
    SQL = "sql"


class ColumnStrategy(StrEnum):
    """How the generator should produce a column value."""

    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    DEFAULT = "default"
    GENERATED = "generated"


class ForeignKeySelectionStrategy(StrEnum):
    """How child rows should choose generated parent keys."""

    BALANCED_FANOUT = "balanced_fanout"
    PROFILE_DRIVEN = "profile_driven"
    RANDOM = "random"


class PlanModel(BaseModel):
    """Base class for immutable generation plan models.

    Plans are frozen on purpose. A generation run should be replayable from the
    same plan and seed, so accidental mutation during row generation is treated as
    a design bug instead of a convenient shortcut.
    """

    model_config = ConfigDict(frozen=True)


class ChildCountFrequency(PlanModel):
    """How many source parents have a specific child count."""

    child_count: int = Field(ge=0)
    parent_frequency: int = Field(gt=0)


class RelationshipFanoutHint(PlanModel):
    """Observed fanout distribution for a foreign-key relationship."""

    child_table: str
    child_columns: tuple[str, ...]
    parent_table: str
    parent_columns: tuple[str, ...]
    child_count_frequencies: tuple[ChildCountFrequency, ...] = ()

    @field_validator("child_table", "parent_table")
    @classmethod
    def require_table_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("relationship hint table names cannot be empty")
        return value

    @field_validator("child_columns", "parent_columns")
    @classmethod
    def require_columns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("relationship hint columns cannot be empty")
        return value


class TopValueHint(PlanModel):
    """Frequent source value for one profiled column."""

    value: str
    count: int = Field(gt=0)


class ColumnProfileHint(PlanModel):
    """Observed source profile for one table column.

    This is the source-agnostic bridge between profilers and generators. A
    PostgreSQL profiler, CSV profiler, or later document-source profiler can all
    emit this contract without forcing `ValueGenerator` to know where the stats
    came from.
    """

    table_name: str
    column_name: str
    sample_count: int = Field(ge=0)
    null_rate: float = Field(ge=0.0, le=1.0)
    distinct_count: int = Field(ge=0)
    min_value: str | None = None
    max_value: str | None = None
    top_values: tuple[TopValueHint, ...] = ()

    @field_validator("table_name", "column_name")
    @classmethod
    def require_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("column profile hint identifiers cannot be empty")
        return value


class ForeignKeySource(PlanModel):
    """Source table and columns for a foreign-key column plan."""

    parent_table: str
    child_columns: tuple[str, ...]
    parent_columns: tuple[str, ...]
    constraint_name: str | None = None
    fanout_hint: RelationshipFanoutHint | None = None


class ColumnPlan(PlanModel):
    """Plan for generating a single table column."""

    name: str
    strategy: ColumnStrategy
    type_family: TypeFamily
    nullable: bool
    default: str | None = None
    foreign_key_source: ForeignKeySource | None = None
    profile_hint: ColumnProfileHint | None = None

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
    """Full deterministic generation plan for a database schema.

    The plan is the backend engine's main handoff object. API routes, CLI commands,
    exporters, validators, and async workers all operate from this same contract.
    """

    seed: int | str
    domain: DomainProfile = DomainProfile.GENERAL
    output_formats: tuple[OutputFormat, ...]
    tables: tuple[TablePlan, ...]
    foreign_key_strategy: ForeignKeySelectionStrategy = (
        ForeignKeySelectionStrategy.BALANCED_FANOUT
    )
    relationship_hints: tuple[RelationshipFanoutHint, ...] = ()
    column_hints: tuple[ColumnProfileHint, ...] = ()

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
    foreign_key_strategy: ForeignKeySelectionStrategy = (
        ForeignKeySelectionStrategy.BALANCED_FANOUT
    ),
    relationship_hints: tuple[RelationshipFanoutHint, ...] = (),
    column_hints: tuple[ColumnProfileHint, ...] = (),
) -> GenerationPlan:
    """Create a deterministic generation plan from schema metadata.

    The builder resolves table order, row counts, key strategies, relationship
    hints, and column profile hints before generation starts. Doing that work here
    keeps the hot row-writing path free from schema lookups.
    """

    if default_row_count < 0:
        raise ValueError("default row count cannot be negative")

    row_counts = row_counts or {}
    _validate_row_count_keys(database, row_counts)

    # The dependency graph gives us parent tables before child tables. That is
    # required because child foreign keys can only point to keys already generated.
    graph = build_relationship_graph(database)
    table_plans = tuple(
        _build_table_plan(
            table,
            graph.parents_for(table),
            row_counts,
            default_row_count,
            relationship_hints,
            column_hints,
        )
        for table in graph.dependency_order()
    )
    return GenerationPlan(
        seed=seed,
        domain=domain,
        output_formats=output_formats,
        tables=table_plans,
        foreign_key_strategy=foreign_key_strategy,
        relationship_hints=relationship_hints,
        column_hints=column_hints,
    )


def _build_table_plan(
    table: TableSchema,
    dependencies,
    row_counts: dict[str, int],
    default_row_count: int,
    relationship_hints: tuple[RelationshipFanoutHint, ...],
    column_hints: tuple[ColumnProfileHint, ...],
) -> TablePlan:
    """Build one table plan from schema columns and known parent dependencies."""

    # A lookup avoids scanning all relationship edges for every column. This keeps
    # plan construction cheap on wide schemas while keeping the row engine simple.
    foreign_key_columns = {
        column_name: (
            edge,
            _relationship_hint_for_edge(edge, relationship_hints),
        )
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
            _build_column_plan(
                column,
                table,
                primary_key_columns,
                foreign_key_columns,
                column_hints,
            )
            for column in table.columns
        ),
    )


def _build_column_plan(
    column: ColumnSchema,
    table: TableSchema,
    primary_key_columns: set[str],
    foreign_key_columns,
    column_hints: tuple[ColumnProfileHint, ...],
) -> ColumnPlan:
    """Choose the generation strategy for one column."""

    profile_hint = _column_hint_for_column(table, column, column_hints)
    if column.name in primary_key_columns:
        return ColumnPlan(
            name=column.name,
            strategy=ColumnStrategy.PRIMARY_KEY,
            type_family=column.data_type.family,
            nullable=column.nullable,
            default=column.default,
            profile_hint=profile_hint,
        )
    if column.name in foreign_key_columns:
        edge, fanout_hint = foreign_key_columns[column.name]
        return ColumnPlan(
            name=column.name,
            strategy=ColumnStrategy.FOREIGN_KEY,
            type_family=column.data_type.family,
            nullable=column.nullable,
            default=column.default,
            profile_hint=profile_hint,
            foreign_key_source=ForeignKeySource(
                parent_table=edge.parent_table,
                child_columns=edge.child_columns,
                parent_columns=edge.parent_columns,
                constraint_name=edge.constraint_name,
                fanout_hint=fanout_hint,
            ),
        )
    return ColumnPlan(
        name=column.name,
        strategy=ColumnStrategy.DEFAULT if column.default is not None else ColumnStrategy.GENERATED,
        type_family=column.data_type.family,
        nullable=column.nullable,
        default=column.default,
        profile_hint=profile_hint,
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


def _relationship_hint_for_edge(
    edge,
    relationship_hints: tuple[RelationshipFanoutHint, ...],
) -> RelationshipFanoutHint | None:
    for hint in relationship_hints:
        if (
            _table_matches(hint.child_table, edge.child_table)
            and _table_matches(hint.parent_table, edge.parent_table)
            and hint.child_columns == edge.child_columns
            and hint.parent_columns == edge.parent_columns
        ):
            return hint
    return None


def _column_hint_for_column(
    table: TableSchema,
    column: ColumnSchema,
    column_hints: tuple[ColumnProfileHint, ...],
) -> ColumnProfileHint | None:
    for hint in column_hints:
        if (
            _table_matches(hint.table_name, table.qualified_name)
            and hint.column_name == column.name
        ):
            return hint
    return None


def _table_matches(hint_table: str, plan_table: str) -> bool:
    return hint_table == plan_table or plan_table.endswith(f".{hint_table}")
