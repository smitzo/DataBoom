import pytest

from boom_data.generation import ColumnStrategy, OutputFormat, create_generation_plan
from boom_data.ingest import parse_postgres_ddl


def test_generation_plan_orders_tables_and_marks_column_strategies() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (
            id bigint PRIMARY KEY,
            name text NOT NULL
        );
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES accounts(id),
            email text NOT NULL,
            created_at timestamp DEFAULT now()
        );
        """
    )

    plan = create_generation_plan(
        database,
        row_counts={"accounts": 2, "public.users": 5},
        seed=123,
        output_formats=(OutputFormat.CSV, OutputFormat.SQL),
    )

    assert [table.table_name for table in plan.tables] == ["public.accounts", "public.users"]
    assert plan.total_rows == 7
    assert plan.table_plan("accounts").row_count == 2
    assert plan.table_plan("users").row_count == 5
    assert plan.table_plan("users").column_plan("id").strategy == ColumnStrategy.PRIMARY_KEY
    assert plan.table_plan("users").column_plan("account_id").strategy == ColumnStrategy.FOREIGN_KEY
    assert plan.table_plan("users").column_plan("email").strategy == ColumnStrategy.GENERATED
    assert plan.table_plan("users").column_plan("created_at").strategy == ColumnStrategy.DEFAULT
    assert plan.table_plan("users").dependencies == ("public.accounts",)


def test_generation_plan_rejects_unknown_row_count_keys() -> None:
    database = parse_postgres_ddl("CREATE TABLE users (id bigint PRIMARY KEY);")

    with pytest.raises(ValueError, match="unknown tables: accounts"):
        create_generation_plan(database, row_counts={"accounts": 10})


def test_generation_plan_rejects_negative_row_counts() -> None:
    database = parse_postgres_ddl("CREATE TABLE users (id bigint PRIMARY KEY);")

    with pytest.raises(ValueError, match="cannot be negative"):
        create_generation_plan(database, row_counts={"users": -1})
