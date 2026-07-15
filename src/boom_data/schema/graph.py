"""Relationship graph utilities for normalized schemas."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from boom_data.schema.models import DatabaseSchema, ForeignKeyConstraint, TableSchema


class SchemaGraphError(ValueError):
    """Raised when a schema relationship graph cannot be built safely."""


class SchemaCycleError(SchemaGraphError):
    """Raised when cross-table dependencies contain a cycle."""


@dataclass(frozen=True)
class RelationshipEdge:
    """Dependency edge from a referenced parent table to a dependent child table."""

    parent_table: str
    child_table: str
    child_columns: tuple[str, ...]
    parent_columns: tuple[str, ...]
    constraint_name: str | None = None

    @property
    def is_self_reference(self) -> bool:
        return self.parent_table == self.child_table


@dataclass(frozen=True)
class RelationshipGraph:
    """Directed relationship graph for generation dependency ordering."""

    database: DatabaseSchema
    edges: tuple[RelationshipEdge, ...]

    def dependency_order(self) -> tuple[TableSchema, ...]:
        """Return tables ordered so parents appear before dependent children."""

        table_by_name = {table.qualified_name: table for table in self.database.tables}
        indegree = {table_name: 0 for table_name in table_by_name}
        children_by_parent: dict[str, set[str]] = defaultdict(set)

        for edge in self.edges:
            if edge.is_self_reference:
                continue
            children_by_parent[edge.parent_table].add(edge.child_table)
            indegree[edge.child_table] += 1

        ready = deque(table_name for table_name, degree in indegree.items() if degree == 0)
        ordered_names: list[str] = []

        while ready:
            table_name = ready.popleft()
            ordered_names.append(table_name)
            for child_name in sorted(children_by_parent[table_name]):
                indegree[child_name] -= 1
                if indegree[child_name] == 0:
                    ready.append(child_name)

        if len(ordered_names) != len(table_by_name):
            blocked = sorted(name for name, degree in indegree.items() if degree > 0)
            raise SchemaCycleError(
                "schema contains cyclic table dependencies: " + ", ".join(blocked)
            )

        return tuple(table_by_name[name] for name in ordered_names)

    def parents_for(self, table: TableSchema) -> tuple[RelationshipEdge, ...]:
        """Return foreign-key edges pointing into a table from its parents."""

        return tuple(edge for edge in self.edges if edge.child_table == table.qualified_name)

    def children_for(self, table: TableSchema) -> tuple[RelationshipEdge, ...]:
        """Return foreign-key edges pointing from a table to its children."""

        return tuple(edge for edge in self.edges if edge.parent_table == table.qualified_name)


def build_relationship_graph(database: DatabaseSchema) -> RelationshipGraph:
    """Build and validate the relationship graph for a database schema."""

    known_tables = set(database.table_names)
    edges: list[RelationshipEdge] = []

    for table in database.tables:
        for foreign_key in table.foreign_keys:
            parent_table = _qualified_referred_table(foreign_key)
            if parent_table not in known_tables:
                raise SchemaGraphError(
                    f"foreign key on {table.qualified_name} references unknown table "
                    f"{parent_table}"
                )
            edges.append(
                RelationshipEdge(
                    parent_table=parent_table,
                    child_table=table.qualified_name,
                    child_columns=foreign_key.columns,
                    parent_columns=foreign_key.referred_columns,
                    constraint_name=foreign_key.name,
                )
            )

    graph = RelationshipGraph(database=database, edges=tuple(edges))
    graph.dependency_order()
    return graph


def _qualified_referred_table(foreign_key: ForeignKeyConstraint) -> str:
    return f"{foreign_key.referred_schema}.{foreign_key.referred_table}"
