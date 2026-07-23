"""Live PostgreSQL schema introspection."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import postgresql

from boom_data.schema import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeyConstraint,
    PostgresType,
    PrimaryKeyConstraint,
    TableSchema,
    UniqueConstraint,
)
from boom_data.schema.models import TypeFamily


def load_postgres_schema(
    database_url: str,
    *,
    schema_names: Iterable[str] = ("public",),
) -> DatabaseSchema:
    """Connect to PostgreSQL and return a normalized schema model."""

    engine = create_engine(database_url)
    try:
        return inspect_postgres_schema(engine, schema_names=schema_names)
    finally:
        engine.dispose()


def inspect_postgres_schema(
    connectable: Any,
    *,
    schema_names: Iterable[str] = ("public",),
) -> DatabaseSchema:
    """Inspect PostgreSQL metadata from an existing SQLAlchemy connectable."""

    inspector = inspect(connectable)
    tables = [
        _inspect_table(inspector, schema_name, table_name)
        for schema_name in schema_names
        for table_name in inspector.get_table_names(schema=schema_name)
    ]
    if not tables:
        raise ValueError("database does not contain any inspectable tables")
    return DatabaseSchema(tables=tuple(tables))


def _inspect_table(inspector: Any, schema_name: str, table_name: str) -> TableSchema:
    return TableSchema(
        schema_name=schema_name,
        name=table_name,
        columns=tuple(
            _column_from_metadata(column)
            for column in inspector.get_columns(table_name, schema=schema_name)
        ),
        primary_key=_primary_key_from_metadata(
            inspector.get_pk_constraint(table_name, schema=schema_name)
        ),
        foreign_keys=tuple(
            _foreign_key_from_metadata(foreign_key)
            for foreign_key in inspector.get_foreign_keys(table_name, schema=schema_name)
        ),
        unique_constraints=tuple(
            _unique_constraint_from_metadata(unique_constraint)
            for unique_constraint in inspector.get_unique_constraints(
                table_name,
                schema=schema_name,
            )
        ),
    )


def _column_from_metadata(column: Mapping[str, Any]) -> ColumnSchema:
    return ColumnSchema(
        name=str(column["name"]),
        data_type=_postgres_type_from_metadata(column["type"]),
        nullable=bool(column.get("nullable", True)),
        default=_optional_string(column.get("default")),
        is_identity=bool(column.get("identity")),
    )


def _primary_key_from_metadata(metadata: Mapping[str, Any]) -> PrimaryKeyConstraint | None:
    columns = tuple(metadata.get("constrained_columns") or ())
    if not columns:
        return None
    return PrimaryKeyConstraint(columns=columns, name=_optional_string(metadata.get("name")))


def _foreign_key_from_metadata(metadata: Mapping[str, Any]) -> ForeignKeyConstraint:
    options = metadata.get("options") or {}
    return ForeignKeyConstraint(
        name=_optional_string(metadata.get("name")),
        columns=tuple(metadata["constrained_columns"]),
        referred_schema=_optional_string(metadata.get("referred_schema")) or "public",
        referred_table=str(metadata["referred_table"]),
        referred_columns=tuple(metadata["referred_columns"]),
        on_delete=_optional_string(options.get("ondelete")),
        on_update=_optional_string(options.get("onupdate")),
    )


def _unique_constraint_from_metadata(metadata: Mapping[str, Any]) -> UniqueConstraint:
    return UniqueConstraint(
        columns=tuple(metadata["column_names"]),
        name=_optional_string(metadata.get("name")),
    )


def _postgres_type_from_metadata(sqlalchemy_type: Any) -> PostgresType:
    raw = _compiled_type(sqlalchemy_type)
    is_array = raw.endswith("[]")
    type_name = raw.removesuffix("[]").split("(", 1)[0].strip().upper()
    return PostgresType(
        raw=raw,
        name=type_name,
        family=_type_family(type_name),
        length=_positive_int(getattr(sqlalchemy_type, "length", None)),
        precision=_positive_int(getattr(sqlalchemy_type, "precision", None)),
        scale=_positive_int(getattr(sqlalchemy_type, "scale", None)),
        is_array=is_array,
    )


def _compiled_type(sqlalchemy_type: Any) -> str:
    try:
        return sqlalchemy_type.compile(dialect=postgresql.dialect())
    except AttributeError:
        return str(sqlalchemy_type)


def _type_family(type_name: str) -> TypeFamily:
    if type_name in {
        "BIGINT",
        "DECIMAL",
        "DOUBLE PRECISION",
        "FLOAT",
        "INTEGER",
        "INT",
        "NUMERIC",
        "REAL",
        "SMALLINT",
    }:
        return TypeFamily.NUMERIC
    if type_name in {"CHAR", "TEXT", "VARCHAR"}:
        return TypeFamily.STRING
    if type_name in {
        "DATE",
        "TIME",
        "TIME WITHOUT TIME ZONE",
        "TIMESTAMP",
        "TIMESTAMP WITHOUT TIME ZONE",
        "TIMESTAMP WITH TIME ZONE",
        "TIMESTAMPTZ",
    }:
        return TypeFamily.DATETIME
    if type_name in {"BOOL", "BOOLEAN"}:
        return TypeFamily.BOOLEAN
    if type_name == "UUID":
        return TypeFamily.UUID
    if type_name in {"JSON", "JSONB"}:
        return TypeFamily.JSON
    return TypeFamily.UNKNOWN


def _positive_int(value: Any) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    return None


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
