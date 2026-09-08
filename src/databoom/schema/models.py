"""Normalized database schema models.

Purpose:
    Define the internal schema contract used by planners, generators, profilers,
    validators, and API responses.

Data flow:
    DDL parser or live introspection -> schema models -> relationship graph ->
    generation plan.

Why this layer exists:
    External sources use different metadata shapes. Normalized frozen models give
    the engine one stable representation to reason about.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TypeFamily(StrEnum):
    """Broad PostgreSQL type families used by generation strategies."""

    BOOLEAN = "boolean"
    DATETIME = "datetime"
    ENUM = "enum"
    JSON = "json"
    NUMERIC = "numeric"
    STRING = "string"
    UUID = "uuid"
    UNKNOWN = "unknown"


class EngineModel(BaseModel):
    """Base model for normalized engine contracts.

    Engine contracts are frozen because schema should not drift while a generation
    plan is being built or executed.
    """

    model_config = ConfigDict(frozen=True)


class PostgresType(EngineModel):
    """Normalized PostgreSQL type information for a column."""

    raw: str
    name: str
    family: TypeFamily = TypeFamily.UNKNOWN
    length: int | None = None
    precision: int | None = None
    scale: int | None = None
    is_array: bool = False

    @field_validator("raw", "name")
    @classmethod
    def require_type_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("type names cannot be empty")
        return value

    @field_validator("length", "precision", "scale")
    @classmethod
    def require_positive_numbers(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("type length, precision, and scale must be positive")
        return value


class ColumnSchema(EngineModel):
    """Normalized column metadata."""

    name: str
    data_type: PostgresType
    nullable: bool = True
    default: str | None = None
    is_identity: bool = False

    @field_validator("name")
    @classmethod
    def require_column_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("column name cannot be empty")
        return value


class PrimaryKeyConstraint(EngineModel):
    """Primary-key constraint for a table."""

    columns: tuple[str, ...]
    name: str | None = None

    @field_validator("columns")
    @classmethod
    def require_columns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("primary key must contain at least one column")
        return value


class UniqueConstraint(EngineModel):
    """Unique constraint for one or more table columns."""

    columns: tuple[str, ...]
    name: str | None = None

    @field_validator("columns")
    @classmethod
    def require_columns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("unique constraint must contain at least one column")
        return value


class ForeignKeyConstraint(EngineModel):
    """Foreign-key relationship from one table to another."""

    columns: tuple[str, ...]
    referred_table: str
    referred_columns: tuple[str, ...]
    name: str | None = None
    referred_schema: str = "public"
    on_delete: str | None = None
    on_update: str | None = None

    @field_validator("columns", "referred_columns")
    @classmethod
    def require_columns(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("foreign key columns cannot be empty")
        return value

    @field_validator("referred_table", "referred_schema")
    @classmethod
    def require_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("foreign key identifiers cannot be empty")
        return value

    @model_validator(mode="after")
    def require_matching_column_counts(self) -> Self:
        if len(self.columns) != len(self.referred_columns):
            raise ValueError("foreign key column count must match referred column count")
        return self


class TableSchema(EngineModel):
    """Normalized table metadata."""

    name: str
    columns: tuple[ColumnSchema, ...]
    schema_name: str = "public"
    primary_key: PrimaryKeyConstraint | None = None
    foreign_keys: tuple[ForeignKeyConstraint, ...] = Field(default_factory=tuple)
    unique_constraints: tuple[UniqueConstraint, ...] = Field(default_factory=tuple)

    @field_validator("name", "schema_name")
    @classmethod
    def require_identifier(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("table identifiers cannot be empty")
        return value

    @field_validator("columns")
    @classmethod
    def require_columns(cls, value: tuple[ColumnSchema, ...]) -> tuple[ColumnSchema, ...]:
        if not value:
            raise ValueError("table must contain at least one column")
        return value

    @model_validator(mode="after")
    def validate_constraint_columns(self) -> Self:
        column_names = self.column_names
        if len(column_names) != len(set(column_names)):
            raise ValueError(f"table {self.qualified_name} contains duplicate column names")

        constraints: list[PrimaryKeyConstraint | UniqueConstraint | ForeignKeyConstraint] = []
        if self.primary_key is not None:
            constraints.append(self.primary_key)
        constraints.extend(self.unique_constraints)
        constraints.extend(self.foreign_keys)

        for constraint in constraints:
            missing = set(constraint.columns) - set(column_names)
            if missing:
                missing_list = ", ".join(sorted(missing))
                raise ValueError(f"constraint references unknown columns: {missing_list}")
        return self

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.name}"

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)

    def get_column(self, name: str) -> ColumnSchema:
        for column in self.columns:
            if column.name == name:
                return column
        raise KeyError(f"column not found: {self.qualified_name}.{name}")


class DatabaseSchema(EngineModel):
    """Normalized database schema used by planners and generators."""

    tables: tuple[TableSchema, ...]

    @field_validator("tables")
    @classmethod
    def require_tables(cls, value: tuple[TableSchema, ...]) -> tuple[TableSchema, ...]:
        if not value:
            raise ValueError("database schema must contain at least one table")
        return value

    @model_validator(mode="after")
    def validate_unique_tables(self) -> Self:
        table_names = self.table_names
        if len(table_names) != len(set(table_names)):
            raise ValueError("database schema contains duplicate table names")
        return self

    @property
    def table_names(self) -> tuple[str, ...]:
        return tuple(table.qualified_name for table in self.tables)

    def get_table(self, name: str, schema_name: str = "public") -> TableSchema:
        qualified_name = f"{schema_name}.{name}"
        for table in self.tables:
            if table.qualified_name == qualified_name:
                return table
        raise KeyError(f"table not found: {qualified_name}")
