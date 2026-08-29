import pytest

from databoom.generation import (
    ForeignKeySelectionStrategy,
    ParentKeyStore,
    RowGenerationError,
    RowGenerator,
    create_generation_plan,
)
from databoom.ingest import parse_postgres_ddl


def rows_by_table(records):
    tables = {}
    for record in records:
        tables.setdefault(record.table_name, []).append(record.row)
    return tables


def test_row_generator_preserves_single_column_foreign_keys() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (
            id bigint PRIMARY KEY,
            name text NOT NULL
        );
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES accounts(id),
            email text NOT NULL
        );
        """
    )
    plan = create_generation_plan(database, row_counts={"accounts": 2, "users": 5}, seed=42)

    tables = rows_by_table(RowGenerator.from_plan(plan).iter_records())

    account_ids = {row["id"] for row in tables["public.accounts"]}
    assert account_ids == {1, 2}
    assert {row["account_id"] for row in tables["public.users"]} <= account_ids
    assert [row["id"] for row in tables["public.users"]] == [1, 2, 3, 4, 5]


def test_row_generator_balances_foreign_key_fanout_by_default() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (
            id bigint PRIMARY KEY,
            name text NOT NULL
        );
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES accounts(id),
            email text NOT NULL
        );
        """
    )
    plan = create_generation_plan(database, row_counts={"accounts": 3, "users": 9}, seed=42)

    tables = rows_by_table(RowGenerator.from_plan(plan).iter_records())
    fanout = {
        account_id: sum(1 for row in tables["public.users"] if row["account_id"] == account_id)
        for account_id in {row["id"] for row in tables["public.accounts"]}
    }

    assert fanout == {1: 3, 2: 3, 3: 3}


def test_row_generator_keeps_sequential_parent_keys_compressed() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (id bigint PRIMARY KEY);
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES accounts(id)
        );
        """
    )
    plan = create_generation_plan(database, row_counts={"accounts": 5, "users": 2}, seed=42)
    generator = RowGenerator.from_plan(plan)

    list(generator.iter_records())
    store = generator.foreign_keys.keys[("public.accounts", ("id",))]

    assert len(store) == 5
    assert store.compressed_sequential is True
    assert store.stored_value_count == 0


def test_row_generator_keeps_random_foreign_key_strategy_available() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (id bigint PRIMARY KEY);
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES accounts(id)
        );
        """
    )
    plan = create_generation_plan(
        database,
        row_counts={"accounts": 2, "users": 6},
        seed=7,
        foreign_key_strategy=ForeignKeySelectionStrategy.RANDOM,
    )

    tables = rows_by_table(RowGenerator.from_plan(plan).iter_records())
    account_ids = {row["id"] for row in tables["public.accounts"]}

    assert {row["account_id"] for row in tables["public.users"]} <= account_ids


def test_row_generator_is_repeatable_for_same_plan() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (id bigint PRIMARY KEY);
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint REFERENCES accounts(id),
            email text NOT NULL
        );
        """
    )
    plan = create_generation_plan(database, row_counts={"accounts": 3, "users": 3}, seed="demo")

    first = list(RowGenerator.from_plan(plan).iter_records())
    second = list(RowGenerator.from_plan(plan).iter_records())

    assert first == second


def test_row_generator_preserves_composite_foreign_keys() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE memberships (
            tenant_id bigint NOT NULL,
            user_id bigint NOT NULL,
            PRIMARY KEY (tenant_id, user_id)
        );
        CREATE TABLE events (
            id bigint PRIMARY KEY,
            tenant_id bigint NOT NULL,
            user_id bigint NOT NULL,
            FOREIGN KEY (tenant_id, user_id) REFERENCES memberships(tenant_id, user_id)
        );
        """
    )
    plan = create_generation_plan(database, row_counts={"memberships": 4, "events": 10}, seed=9)

    tables = rows_by_table(RowGenerator.from_plan(plan).iter_records())
    membership_keys = {
        (row["tenant_id"], row["user_id"])
        for row in tables["public.memberships"]
    }
    event_keys = {
        (row["tenant_id"], row["user_id"])
        for row in tables["public.events"]
    }

    assert event_keys <= membership_keys


def test_row_generator_rejects_child_rows_without_parent_keys() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (id bigint PRIMARY KEY);
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint REFERENCES accounts(id)
        );
        """
    )
    plan = create_generation_plan(database, row_counts={"accounts": 0, "users": 1}, seed=42)

    with pytest.raises(RowGenerationError, match="no generated parent keys"):
        list(RowGenerator.from_plan(plan).iter_records())


def test_parent_key_store_compresses_sequential_integer_keys() -> None:
    store = ParentKeyStore()

    for value in range(1, 6):
        store.append((value,))

    assert len(store) == 5
    assert store.compressed_sequential is True
    assert store.stored_value_count == 0
    assert store.get(3) == (4,)


def test_parent_key_store_materializes_when_sequence_breaks() -> None:
    store = ParentKeyStore()

    store.append((1,))
    store.append((2,))
    store.append((9,))

    assert len(store) == 3
    assert store.compressed_sequential is False
    assert store.stored_value_count == 3
    assert store.get(0) == (1,)
    assert store.get(2) == (9,)
