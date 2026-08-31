import pytest

from databoom.generation import (
    ChildCountFrequency,
    ColumnProfileHint,
    ColumnStrategy,
    ForeignKeySelectionStrategy,
    OutputFormat,
    RelationshipFanoutHint,
    create_generation_plan,
)
from databoom.ingest import parse_postgres_ddl


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
    assert plan.foreign_key_strategy == ForeignKeySelectionStrategy.BALANCED_FANOUT


def test_generation_plan_rejects_unknown_row_count_keys() -> None:
    database = parse_postgres_ddl("CREATE TABLE users (id bigint PRIMARY KEY);")

    with pytest.raises(ValueError, match="unknown tables: accounts"):
        create_generation_plan(database, row_counts={"accounts": 10})


def test_generation_plan_rejects_negative_row_counts() -> None:
    database = parse_postgres_ddl("CREATE TABLE users (id bigint PRIMARY KEY);")

    with pytest.raises(ValueError, match="cannot be negative"):
        create_generation_plan(database, row_counts={"users": -1})


def test_generation_plan_allows_random_foreign_key_strategy() -> None:
    database = parse_postgres_ddl("CREATE TABLE users (id bigint PRIMARY KEY);")

    plan = create_generation_plan(
        database,
        foreign_key_strategy=ForeignKeySelectionStrategy.RANDOM,
    )

    assert plan.foreign_key_strategy == ForeignKeySelectionStrategy.RANDOM


def test_generation_plan_attaches_relationship_fanout_hints() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (id bigint PRIMARY KEY);
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES accounts(id)
        );
        """
    )
    hint = RelationshipFanoutHint(
        child_table="public.users",
        child_columns=("account_id",),
        parent_table="public.accounts",
        parent_columns=("id",),
        child_count_frequencies=(
            ChildCountFrequency(child_count=0, parent_frequency=1),
            ChildCountFrequency(child_count=3, parent_frequency=2),
        ),
    )

    plan = create_generation_plan(
        database,
        relationship_hints=(hint,),
        foreign_key_strategy=ForeignKeySelectionStrategy.PROFILE_DRIVEN,
    )
    source = plan.table_plan("users").column_plan("account_id").foreign_key_source

    assert plan.relationship_hints == (hint,)
    assert plan.foreign_key_strategy == ForeignKeySelectionStrategy.PROFILE_DRIVEN
    assert source is not None
    assert source.fanout_hint == hint


def test_generation_plan_attaches_column_profile_hints() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE customers (
            id bigint PRIMARY KEY,
            status text NOT NULL
        );
        """
    )
    hint = ColumnProfileHint(
        table_name="public.customers",
        column_name="status",
        sample_count=100,
        null_rate=0.0,
        distinct_count=3,
        min_value="active",
        max_value="pending",
    )

    plan = create_generation_plan(database, column_hints=(hint,))
    column = plan.table_plan("customers").column_plan("status")

    assert plan.column_hints == (hint,)
    assert column.profile_hint == hint
