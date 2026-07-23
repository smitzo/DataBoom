from datetime import datetime

import pytest

from databoom.generation import ColumnStrategy, ForeignKeySource, SeedManager, ValueGenerator
from databoom.generation.plan import ColumnPlan
from databoom.schema import TypeFamily


def column(
    name: str,
    family: TypeFamily,
    *,
    strategy: ColumnStrategy = ColumnStrategy.GENERATED,
    nullable: bool = False,
) -> ColumnPlan:
    return ColumnPlan(name=name, strategy=strategy, type_family=family, nullable=nullable)


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
