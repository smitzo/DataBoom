import pytest

from databoom.schema import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeyConstraint,
    PostgresType,
    TableSchema,
    build_relationship_graph,
)
from databoom.schema.graph import SchemaCycleError, SchemaGraphError


def column(name: str) -> ColumnSchema:
    return ColumnSchema(name=name, data_type=PostgresType(raw="bigint", name="BIGINT"))


def table(name: str, foreign_keys: tuple[ForeignKeyConstraint, ...] = ()) -> TableSchema:
    return TableSchema(name=name, columns=(column("id"),), foreign_keys=foreign_keys)


def fk(column_name: str, referred_table: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        columns=(column_name,),
        referred_table=referred_table,
        referred_columns=("id",),
    )


def test_relationship_graph_orders_parents_before_children() -> None:
    accounts = table("accounts")
    users = TableSchema(
        name="users",
        columns=(column("id"), column("account_id")),
        foreign_keys=(fk("account_id", "accounts"),),
    )
    orders = TableSchema(
        name="orders",
        columns=(column("id"), column("user_id")),
        foreign_keys=(fk("user_id", "users"),),
    )
    graph = build_relationship_graph(DatabaseSchema(tables=(orders, users, accounts)))

    assert [table.name for table in graph.dependency_order()] == ["accounts", "users", "orders"]
    assert graph.parents_for(orders)[0].parent_table == "public.users"
    assert graph.children_for(accounts)[0].child_table == "public.users"


def test_relationship_graph_supports_join_tables_with_multiple_parents() -> None:
    users = table("users")
    teams = table("teams")
    memberships = TableSchema(
        name="memberships",
        columns=(column("id"), column("user_id"), column("team_id")),
        foreign_keys=(fk("user_id", "users"), fk("team_id", "teams")),
    )
    graph = build_relationship_graph(DatabaseSchema(tables=(memberships, teams, users)))

    ordered_names = [table.name for table in graph.dependency_order()]

    assert ordered_names[-1] == "memberships"
    assert set(ordered_names[:2]) == {"teams", "users"}


def test_relationship_graph_ignores_self_references_for_dependency_order() -> None:
    categories = TableSchema(
        name="categories",
        columns=(column("id"), column("parent_id")),
        foreign_keys=(fk("parent_id", "categories"),),
    )
    graph = build_relationship_graph(DatabaseSchema(tables=(categories,)))

    assert [table.name for table in graph.dependency_order()] == ["categories"]
    assert graph.edges[0].is_self_reference is True


def test_relationship_graph_rejects_unknown_referenced_table() -> None:
    users = TableSchema(
        name="users",
        columns=(column("id"), column("account_id")),
        foreign_keys=(fk("account_id", "accounts"),),
    )

    with pytest.raises(SchemaGraphError, match="references unknown table public.accounts"):
        build_relationship_graph(DatabaseSchema(tables=(users,)))


def test_relationship_graph_rejects_cross_table_cycles() -> None:
    left = TableSchema(
        name="left",
        columns=(column("id"), column("right_id")),
        foreign_keys=(fk("right_id", "right"),),
    )
    right = TableSchema(
        name="right",
        columns=(column("id"), column("left_id")),
        foreign_keys=(fk("left_id", "left"),),
    )

    with pytest.raises(SchemaCycleError, match="cyclic table dependencies"):
        build_relationship_graph(DatabaseSchema(tables=(left, right)))
