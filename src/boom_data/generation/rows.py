"""Relationship-aware row generation."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from boom_data.generation.plan import (
    ColumnStrategy,
    ForeignKeySource,
    GenerationPlan,
    TablePlan,
)
from boom_data.generation.seed import SeedManager
from boom_data.generation.values import GeneratedValue, ValueGenerator

type GeneratedRow = dict[str, GeneratedValue]


class RowGenerationError(ValueError):
    """Raised when rows cannot be generated from a plan."""


@dataclass(frozen=True)
class GeneratedRecord:
    """One generated row with its table context."""

    table_name: str
    row: GeneratedRow


@dataclass
class ForeignKeyRegistry:
    """Store generated parent key values for child-table foreign keys."""

    keys: dict[tuple[str, tuple[str, ...]], list[tuple[Any, ...]]] = field(default_factory=dict)

    def register(self, table: TablePlan, row: GeneratedRow) -> None:
        primary_key_columns = tuple(
            column.name for column in table.columns if column.strategy == ColumnStrategy.PRIMARY_KEY
        )
        if not primary_key_columns:
            return

        key = (table.table_name, primary_key_columns)
        self.keys.setdefault(key, []).append(tuple(row[column] for column in primary_key_columns))

    def choose(
        self,
        source: ForeignKeySource,
        *,
        seed_manager: SeedManager,
        table_name: str,
        row_index: int,
    ) -> tuple[Any, ...]:
        key = (source.parent_table, source.parent_columns)
        values = self.keys.get(key, [])
        if not values:
            raise RowGenerationError(
                f"no generated parent keys for {source.parent_table}"
                f"({', '.join(source.parent_columns)})"
            )

        stream = seed_manager.stream("foreign-key", table_name, source.parent_table, row_index)
        return values[stream.randrange(len(values))]


@dataclass
class RowGenerator:
    """Execute a generation plan into deterministic table rows."""

    plan: GenerationPlan
    seed_manager: SeedManager
    value_generator: ValueGenerator
    foreign_keys: ForeignKeyRegistry = field(default_factory=ForeignKeyRegistry)

    @classmethod
    def from_plan(cls, plan: GenerationPlan) -> RowGenerator:
        seed_manager = SeedManager(plan.seed)
        return cls(
            plan=plan,
            seed_manager=seed_manager,
            value_generator=ValueGenerator(seed_manager),
        )

    def iter_records(self) -> Iterator[GeneratedRecord]:
        """Yield generated rows in table dependency order."""

        for table in self.plan.tables:
            for row_index in range(table.row_count):
                row = self._generate_row(table, row_index)
                self.foreign_keys.register(table, row)
                yield GeneratedRecord(table_name=table.table_name, row=row)

    def _generate_row(self, table: TablePlan, row_index: int) -> GeneratedRow:
        row: GeneratedRow = {}
        foreign_key_values = self._foreign_key_values_for_row(table, row_index)

        for column in table.columns:
            if column.strategy == ColumnStrategy.FOREIGN_KEY:
                row[column.name] = foreign_key_values[column.name]
            else:
                row[column.name] = self.value_generator.value_for(
                    table.table_name,
                    column,
                    row_index,
                )
        return row

    def _foreign_key_values_for_row(
        self,
        table: TablePlan,
        row_index: int,
    ) -> dict[str, GeneratedValue]:
        values: dict[str, GeneratedValue] = {}
        for source in _unique_foreign_key_sources(table):
            parent_values = self.foreign_keys.choose(
                source,
                seed_manager=self.seed_manager,
                table_name=table.table_name,
                row_index=row_index,
            )
            for child_column, value in zip(source.child_columns, parent_values, strict=True):
                values[child_column] = value
        return values


def _unique_foreign_key_sources(table: TablePlan) -> tuple[ForeignKeySource, ...]:
    sources: list[ForeignKeySource] = []
    seen: set[tuple[str, tuple[str, ...], tuple[str, ...]]] = set()

    for column in table.columns:
        if column.foreign_key_source is None:
            continue
        key = (
            column.foreign_key_source.parent_table,
            column.foreign_key_source.child_columns,
            column.foreign_key_source.parent_columns,
        )
        if key not in seen:
            seen.add(key)
            sources.append(column.foreign_key_source)
    return tuple(sources)
