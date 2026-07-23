import pytest
from pydantic import ValidationError

from databoom.schema import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeyConstraint,
    PostgresType,
    PrimaryKeyConstraint,
    TableSchema,
    UniqueConstraint,
)
from databoom.schema.models import TypeFamily


def pg_type(name: str, family: TypeFamily = TypeFamily.UNKNOWN) -> PostgresType:
    return PostgresType(raw=name, name=name, family=family)


def column(name: str, family: TypeFamily = TypeFamily.STRING) -> ColumnSchema:
    return ColumnSchema(name=name, data_type=pg_type("text", family), nullable=False)


def test_table_schema_exposes_columns_and_qualified_name() -> None:
    table = TableSchema(
        name="users",
        columns=(column("id", TypeFamily.UUID), column("email")),
        primary_key=PrimaryKeyConstraint(columns=("id",)),
        unique_constraints=(UniqueConstraint(columns=("email",)),),
    )

    assert table.qualified_name == "public.users"
    assert table.column_names == ("id", "email")
    assert table.get_column("email").name == "email"


def test_table_schema_rejects_duplicate_columns() -> None:
    with pytest.raises(ValidationError, match="duplicate column names"):
        TableSchema(name="users", columns=(column("id"), column("id")))


def test_table_schema_rejects_unknown_constraint_columns() -> None:
    with pytest.raises(ValidationError, match="unknown columns: account_id"):
        TableSchema(
            name="users",
            columns=(column("id"),),
            foreign_keys=(
                ForeignKeyConstraint(
                    columns=("account_id",),
                    referred_table="accounts",
                    referred_columns=("id",),
                ),
            ),
        )


def test_foreign_key_requires_matching_column_counts() -> None:
    with pytest.raises(ValidationError, match="column count must match"):
        ForeignKeyConstraint(
            columns=("tenant_id", "account_id"),
            referred_table="accounts",
            referred_columns=("id",),
        )


def test_database_schema_rejects_duplicate_tables() -> None:
    users = TableSchema(name="users", columns=(column("id"),))

    with pytest.raises(ValidationError, match="duplicate table names"):
        DatabaseSchema(tables=(users, users))


def test_database_schema_lookup_uses_schema_and_table_name() -> None:
    users = TableSchema(schema_name="app", name="users", columns=(column("id"),))
    database = DatabaseSchema(tables=(users,))

    assert database.table_names == ("app.users",)
    assert database.get_table("users", schema_name="app") == users
