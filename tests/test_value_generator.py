from datetime import datetime

import pytest

from databoom.generation import (
    ColumnProfileHint,
    ColumnStrategy,
    DomainProfile,
    ForeignKeySource,
    SeedManager,
    TopValueHint,
    ValueGenerator,
)
from databoom.generation.plan import ColumnPlan
from databoom.schema import TypeFamily


def column(
    name: str,
    family: TypeFamily,
    *,
    strategy: ColumnStrategy = ColumnStrategy.GENERATED,
    nullable: bool = False,
    profile_hint: ColumnProfileHint | None = None,
) -> ColumnPlan:
    return ColumnPlan(
        name=name,
        strategy=strategy,
        type_family=family,
        nullable=nullable,
        profile_hint=profile_hint,
    )


def test_value_generator_returns_repeatable_values() -> None:
    value_generator = ValueGenerator(SeedManager(42))
    email = column("email", TypeFamily.STRING)

    assert value_generator.value_for("public.users", email, 0) == value_generator.value_for(
        "public.users", email, 0
    )
    assert value_generator.value_for("public.users", email, 0) != value_generator.value_for(
        "public.users", email, 1
    )


def test_value_generator_handles_common_type_families() -> None:
    value_generator = ValueGenerator(SeedManager("demo"))

    assert isinstance(
        value_generator.value_for("public.users", column("flag", TypeFamily.BOOLEAN), 0),
        bool,
    )
    assert isinstance(
        value_generator.value_for("public.users", column("count", TypeFamily.NUMERIC), 0),
        int,
    )
    assert isinstance(
        value_generator.value_for("public.users", column("seen_at", TypeFamily.DATETIME), 0),
        datetime,
    )
    assert isinstance(
        value_generator.value_for("public.users", column("meta", TypeFamily.JSON), 0),
        dict,
    )
    assert "@" in str(
        value_generator.value_for("public.users", column("email", TypeFamily.STRING), 0)
    )


def test_value_generator_uses_sequence_for_numeric_primary_keys() -> None:
    value_generator = ValueGenerator(SeedManager(42))
    id_column = column("id", TypeFamily.NUMERIC, strategy=ColumnStrategy.PRIMARY_KEY)

    assert [value_generator.value_for("public.users", id_column, index) for index in range(3)] == [
        1,
        2,
        3,
    ]


def test_value_generator_can_emit_null_for_nullable_columns() -> None:
    value_generator = ValueGenerator(SeedManager(42), null_probability=1.0)

    assert (
        value_generator.value_for(
            "public.users",
            column("nickname", TypeFamily.STRING, nullable=True),
            0,
        )
        is None
    )
    assert (
        value_generator.value_for("public.users", column("name", TypeFamily.STRING), 0)
        is not None
    )


def test_value_generator_uses_profile_null_rate_for_nullable_columns() -> None:
    value_generator = ValueGenerator(SeedManager(42), null_probability=0.0)
    profile_hint = ColumnProfileHint(
        table_name="public.users",
        column_name="nickname",
        sample_count=100,
        null_rate=1.0,
        distinct_count=0,
    )

    assert (
        value_generator.value_for(
            "public.users",
            column("nickname", TypeFamily.STRING, nullable=True, profile_hint=profile_hint),
            0,
        )
        is None
    )


def test_value_generator_samples_categorical_profile_top_values() -> None:
    value_generator = ValueGenerator(SeedManager(42))
    profile_hint = ColumnProfileHint(
        table_name="public.users",
        column_name="status",
        sample_count=100,
        null_rate=0.0,
        distinct_count=2,
        top_values=(
            TopValueHint(value="active", count=80),
            TopValueHint(value="inactive", count=20),
        ),
    )
    status_column = column("status", TypeFamily.STRING, profile_hint=profile_hint)
    values = [
        value_generator.value_for("public.users", status_column, row_index)
        for row_index in range(100)
    ]

    assert set(values) == {"active", "inactive"}
    assert values.count("active") > values.count("inactive")


def test_value_generator_profile_top_values_override_domain_provider() -> None:
    value_generator = ValueGenerator(SeedManager(42), domain=DomainProfile.FINANCIAL)
    profile_hint = ColumnProfileHint(
        table_name="public.transactions",
        column_name="status",
        sample_count=10,
        null_rate=0.0,
        distinct_count=1,
        top_values=(TopValueHint(value="settled", count=10),),
    )

    assert value_generator.value_for(
        "public.transactions",
        column("status", TypeFamily.STRING, profile_hint=profile_hint),
        0,
    ) == "settled"


def test_value_generator_uses_profile_integer_numeric_range() -> None:
    value_generator = ValueGenerator(SeedManager(42))
    profile_hint = ColumnProfileHint(
        table_name="public.orders",
        column_name="quantity",
        sample_count=100,
        null_rate=0.0,
        distinct_count=3,
        min_value="1",
        max_value="3",
    )
    quantity_column = column("quantity", TypeFamily.NUMERIC, profile_hint=profile_hint)
    values = [
        value_generator.value_for("public.orders", quantity_column, row_index)
        for row_index in range(30)
    ]

    assert all(isinstance(value, int) for value in values)
    assert all(1 <= value <= 3 for value in values)


def test_value_generator_uses_profile_decimal_range_before_domain_provider() -> None:
    value_generator = ValueGenerator(SeedManager(42), domain=DomainProfile.FINANCIAL)
    profile_hint = ColumnProfileHint(
        table_name="public.transactions",
        column_name="amount",
        sample_count=100,
        null_rate=0.0,
        distinct_count=80,
        min_value="5.25",
        max_value="7.75",
    )
    amount_column = column("amount", TypeFamily.NUMERIC, profile_hint=profile_hint)
    values = [
        value_generator.value_for("public.transactions", amount_column, row_index)
        for row_index in range(30)
    ]

    assert all(isinstance(value, float) for value in values)
    assert all(5.25 <= value <= 7.75 for value in values)


def test_value_generator_uses_profile_datetime_range() -> None:
    value_generator = ValueGenerator(SeedManager(42))
    profile_hint = ColumnProfileHint(
        table_name="public.events",
        column_name="seen_at",
        sample_count=100,
        null_rate=0.0,
        distinct_count=100,
        min_value="2024-01-01T00:00:00Z",
        max_value="2024-01-03T00:00:00Z",
    )
    seen_at_column = column("seen_at", TypeFamily.DATETIME, profile_hint=profile_hint)
    values = [
        value_generator.value_for("public.events", seen_at_column, row_index)
        for row_index in range(30)
    ]
    minimum = datetime.fromisoformat("2024-01-01T00:00:00+00:00")
    maximum = datetime.fromisoformat("2024-01-03T00:00:00+00:00")

    assert all(isinstance(value, datetime) for value in values)
    assert all(minimum <= value <= maximum for value in values)


def test_value_generator_rejects_foreign_key_columns() -> None:
    value_generator = ValueGenerator(SeedManager(42))
    account_id = ColumnPlan(
        name="account_id",
        strategy=ColumnStrategy.FOREIGN_KEY,
        type_family=TypeFamily.NUMERIC,
        nullable=False,
        foreign_key_source=ForeignKeySource(
            parent_table="public.accounts",
            child_columns=("account_id",),
            parent_columns=("id",),
        ),
    )

    with pytest.raises(ValueError, match="relationship solver"):
        value_generator.value_for("public.users", account_id, 0)
