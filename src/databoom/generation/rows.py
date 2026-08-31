"""Relationship-aware row generation."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from math import gcd
from typing import Any

from databoom.generation.plan import (
    ColumnStrategy,
    ForeignKeySelectionStrategy,
    ForeignKeySource,
    GenerationPlan,
    TablePlan,
)
from databoom.generation.seed import SeedManager
from databoom.generation.values import GeneratedValue, ValueGenerator

type GeneratedRow = dict[str, GeneratedValue]


class RowGenerationError(ValueError):
    """Raised when rows cannot be generated from a plan."""


@dataclass(frozen=True)
class GeneratedRecord:
    """One generated row with its table context."""

    table_name: str
    row: GeneratedRow


@dataclass
class ParentKeyStore:
    """Store parent keys, compressing the common sequential integer key path."""

    values: list[tuple[Any, ...]] = field(default_factory=list)
    sequential_count: int = 0
    compressed_sequential: bool = True

    def append(self, key: tuple[Any, ...]) -> None:
        if self.compressed_sequential and _is_next_sequential_key(
            key,
            self.sequential_count + 1,
        ):
            self.sequential_count += 1
            return

        if self.compressed_sequential:
            self.values = [(value,) for value in range(1, self.sequential_count + 1)]
            self.compressed_sequential = False
        self.values.append(key)

    def __len__(self) -> int:
        if self.compressed_sequential:
            return self.sequential_count
        return len(self.values)

    def get(self, index: int) -> tuple[Any, ...]:
        if self.compressed_sequential:
            if not 0 <= index < self.sequential_count:
                raise IndexError(index)
            return (index + 1,)
        return self.values[index]

    @property
    def stored_value_count(self) -> int:
        """Return how many key tuples are materialized in memory."""

        return len(self.values)


@dataclass
class ForeignKeyRegistry:
    """Store generated parent key values for child-table foreign keys."""

    keys: dict[tuple[str, tuple[str, ...]], ParentKeyStore] = field(default_factory=dict)
    balanced_plans: dict[
        tuple[str, str, tuple[str, ...], tuple[str, ...]],
        tuple[int, int],
    ] = field(default_factory=dict)
    profile_plans: dict[
        tuple[str, str, tuple[str, ...], tuple[str, ...], int, int],
        tuple[int, ...],
    ] = field(default_factory=dict)

    def register(self, table: TablePlan, row: GeneratedRow) -> None:
        primary_key_columns = tuple(
            column.name for column in table.columns if column.strategy == ColumnStrategy.PRIMARY_KEY
        )
        if not primary_key_columns:
            return

        key = (table.table_name, primary_key_columns)
        self.keys.setdefault(key, ParentKeyStore()).append(
            tuple(row[column] for column in primary_key_columns)
        )

    def choose(
        self,
        source: ForeignKeySource,
        *,
        seed_manager: SeedManager,
        strategy: ForeignKeySelectionStrategy,
        table_name: str,
        row_index: int,
        child_row_count: int,
    ) -> tuple[Any, ...]:
        key = (source.parent_table, source.parent_columns)
        store = self.keys.get(key)
        if store is None or len(store) == 0:
            raise RowGenerationError(
                f"no generated parent keys for {source.parent_table}"
                f"({', '.join(source.parent_columns)})"
            )

        if strategy == ForeignKeySelectionStrategy.RANDOM:
            stream = seed_manager.stream(
                "foreign-key-random",
                table_name,
                source.parent_table,
                row_index,
            )
            return store.get(stream.randrange(len(store)))

        if strategy == ForeignKeySelectionStrategy.PROFILE_DRIVEN:
            profile_index = self._profile_index(
                source,
                seed_manager=seed_manager,
                table_name=table_name,
                parent_count=len(store),
                child_row_count=child_row_count,
                row_index=row_index,
            )
            if profile_index is not None:
                return store.get(profile_index)

        index = self._balanced_index(
            source,
            seed_manager=seed_manager,
            table_name=table_name,
            parent_count=len(store),
            row_index=row_index,
        )
        return store.get(index)

    def _balanced_index(
        self,
        source: ForeignKeySource,
        *,
        seed_manager: SeedManager,
        table_name: str,
        parent_count: int,
        row_index: int,
    ) -> int:
        if parent_count == 1:
            return 0

        cache_key = (
            table_name,
            source.parent_table,
            source.child_columns,
            source.parent_columns,
        )
        if cache_key not in self.balanced_plans:
            stream = seed_manager.stream(
                "foreign-key-balanced",
                table_name,
                source.parent_table,
                ",".join(source.child_columns),
                ",".join(source.parent_columns),
            )
            offset = stream.randrange(parent_count)
            stride = _coprime_stride(parent_count, stream.randrange(1, parent_count))
            self.balanced_plans[cache_key] = (offset, stride)

        offset, stride = self.balanced_plans[cache_key]
        return (offset + (row_index * stride)) % parent_count

    def _profile_index(
        self,
        source: ForeignKeySource,
        *,
        seed_manager: SeedManager,
        table_name: str,
        parent_count: int,
        child_row_count: int,
        row_index: int,
    ) -> int | None:
        if source.fanout_hint is None or not source.fanout_hint.child_count_frequencies:
            return None
        if child_row_count <= 0:
            return None

        cache_key = (
            table_name,
            source.parent_table,
            source.child_columns,
            source.parent_columns,
            parent_count,
            child_row_count,
        )
        if cache_key not in self.profile_plans:
            self.profile_plans[cache_key] = _profile_parent_indexes(
                source,
                seed_manager=seed_manager,
                table_name=table_name,
                parent_count=parent_count,
                child_row_count=child_row_count,
            )

        parent_indexes = self.profile_plans[cache_key]
        if not parent_indexes or row_index >= len(parent_indexes):
            return None
        return parent_indexes[row_index]


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
            value_generator=ValueGenerator(seed_manager, domain=plan.domain),
        )

    def iter_records(self) -> Iterator[GeneratedRecord]:
        """Yield generated rows in table dependency order."""

        for table in self.plan.tables:
            for row in self.iter_table_rows(table):
                yield GeneratedRecord(table_name=table.table_name, row=row)

    def iter_table_rows(self, table: TablePlan) -> Iterator[GeneratedRow]:
        """Yield generated rows for the next table in dependency order."""

        for row_index in range(table.row_count):
            row = self._generate_row(table, row_index)
            self.foreign_keys.register(table, row)
            yield row

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
                strategy=self.plan.foreign_key_strategy,
                table_name=table.table_name,
                row_index=row_index,
                child_row_count=table.row_count,
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


def _coprime_stride(parent_count: int, candidate: int) -> int:
    if parent_count <= 2:
        return 1

    stride = max(1, candidate % parent_count)
    while gcd(stride, parent_count) != 1:
        stride = (stride + 1) % parent_count
        if stride == 0:
            stride = 1
    return stride


def _profile_parent_indexes(
    source: ForeignKeySource,
    *,
    seed_manager: SeedManager,
    table_name: str,
    parent_count: int,
    child_row_count: int,
) -> tuple[int, ...]:
    frequencies = tuple(
        (frequency.child_count, frequency.parent_frequency)
        for frequency in source.fanout_hint.child_count_frequencies
        if frequency.parent_frequency > 0
    ) if source.fanout_hint is not None else ()
    if not frequencies:
        return ()

    child_count_classes = _scale_frequency_classes(frequencies, parent_count)
    parent_order = _permuted_indices(
        parent_count,
        seed_manager=seed_manager,
        stream_parts=(
            "foreign-key-profile-parents",
            table_name,
            source.parent_table,
            ",".join(source.child_columns),
            ",".join(source.parent_columns),
        ),
    )
    profile_counts_by_parent = [0] * parent_count
    for position, child_count in enumerate(child_count_classes):
        profile_counts_by_parent[parent_order[position]] = child_count

    generated_counts_by_parent = _scale_child_counts(
        profile_counts_by_parent,
        child_row_count,
        parent_order,
    )
    child_parent_order = _permuted_indices(
        parent_count,
        seed_manager=seed_manager,
        stream_parts=(
            "foreign-key-profile-children",
            table_name,
            source.parent_table,
            ",".join(source.child_columns),
            ",".join(source.parent_columns),
        ),
    )

    parent_indexes: list[int] = []
    for parent_index in child_parent_order:
        parent_indexes.extend([parent_index] * generated_counts_by_parent[parent_index])
    return tuple(parent_indexes)


def _scale_frequency_classes(
    frequencies: tuple[tuple[int, int], ...],
    parent_count: int,
) -> tuple[int, ...]:
    total_frequency = sum(frequency for _, frequency in frequencies)
    if total_frequency <= 0 or parent_count <= 0:
        return ()

    allocations = [
        [
            child_count,
            (parent_count * frequency) // total_frequency,
            (parent_count * frequency) % total_frequency,
        ]
        for child_count, frequency in sorted(frequencies)
    ]
    remaining = parent_count - sum(allocation[1] for allocation in allocations)
    for allocation in sorted(allocations, key=lambda item: (-item[2], item[0]))[:remaining]:
        allocation[1] += 1

    classes: list[int] = []
    for child_count, frequency, _ in allocations:
        classes.extend([child_count] * frequency)
    return tuple(classes[:parent_count])


def _scale_child_counts(
    profile_counts_by_parent: list[int],
    child_row_count: int,
    parent_order: tuple[int, ...],
) -> list[int]:
    if child_row_count <= 0:
        return [0] * len(profile_counts_by_parent)

    profile_child_total = sum(profile_counts_by_parent)
    if profile_child_total <= 0:
        counts = [0] * len(profile_counts_by_parent)
        for offset in range(child_row_count):
            counts[parent_order[offset % len(parent_order)]] += 1
        return counts

    scaled = [
        (child_count * child_row_count) // profile_child_total
        for child_count in profile_counts_by_parent
    ]
    remainders = [
        (child_count * child_row_count) % profile_child_total
        for child_count in profile_counts_by_parent
    ]
    remaining = child_row_count - sum(scaled)
    parent_rank = {parent_index: rank for rank, parent_index in enumerate(parent_order)}
    for parent_index in sorted(
        range(len(profile_counts_by_parent)),
        key=lambda index: (-remainders[index], parent_rank[index]),
    )[:remaining]:
        scaled[parent_index] += 1
    return scaled


def _permuted_indices(
    count: int,
    *,
    seed_manager: SeedManager,
    stream_parts: tuple[str, ...],
) -> tuple[int, ...]:
    if count <= 0:
        return ()
    if count == 1:
        return (0,)

    stream = seed_manager.stream(*stream_parts)
    offset = stream.randrange(count)
    stride = _coprime_stride(count, stream.randrange(1, count))
    return tuple((offset + (index * stride)) % count for index in range(count))


def _is_next_sequential_key(key: tuple[Any, ...], expected_value: int) -> bool:
    if len(key) != 1:
        return False

    value = key[0]
    return isinstance(value, int) and not isinstance(value, bool) and value == expected_value
