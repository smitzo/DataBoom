"""Validation for local generated artifacts.

Purpose:
    Re-read generated artifact files and produce a machine-readable validation
    report for row counts, required values, primary keys, foreign keys, and fanout.

Data flow:
    `GenerationPlan` + `ExportManifest` -> CSV artifact reads -> validation issues
    and relationship metrics -> `validation.json`.

Why this layer exists:
    Validation intentionally checks the files on disk, not only the in-memory row
    stream. That catches exporter bugs, partial writes, and artifact path problems
    that a pure generation-unit test would miss.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from databoom.export import ExportManifest, TableArtifact
from databoom.generation import ColumnStrategy
from databoom.generation.plan import GenerationPlan, TablePlan


@dataclass(frozen=True)
class ValidationIssue:
    """One validation issue found in generated artifacts."""

    code: str
    message: str
    table_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "table_name": self.table_name,
        }


@dataclass(frozen=True)
class RelationshipFanoutMetric:
    """Fanout distribution for one generated foreign-key relationship."""

    child_table: str
    child_columns: tuple[str, ...]
    parent_table: str
    parent_columns: tuple[str, ...]
    parent_key_count: int
    child_row_count: int
    min_children_per_parent: int
    max_children_per_parent: int
    average_children_per_parent: float
    empty_parent_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "child_table": self.child_table,
            "child_columns": list(self.child_columns),
            "parent_table": self.parent_table,
            "parent_columns": list(self.parent_columns),
            "parent_key_count": self.parent_key_count,
            "child_row_count": self.child_row_count,
            "min_children_per_parent": self.min_children_per_parent,
            "max_children_per_parent": self.max_children_per_parent,
            "average_children_per_parent": self.average_children_per_parent,
            "empty_parent_count": self.empty_parent_count,
        }


@dataclass(frozen=True)
class ValidationReport:
    """Machine-readable validation result.

    The report is designed for both humans and automation: API responses can show
    a compact summary while CI or future quality gates can inspect issue codes.
    """

    passed: bool
    issues: tuple[ValidationIssue, ...]
    checked_tables: tuple[str, ...]
    relationship_metrics: tuple[RelationshipFanoutMetric, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checked_tables": list(self.checked_tables),
            "issues": [issue.to_dict() for issue in self.issues],
            "relationship_metrics": [
                metric.to_dict() for metric in self.relationship_metrics
            ],
        }

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def validate_export(plan: GenerationPlan, manifest: ExportManifest) -> ValidationReport:
    """Validate local artifacts against a generation plan."""

    issues: list[ValidationIssue] = []
    table_artifacts = {artifact.table_name: artifact for artifact in manifest.tables}
    referenced_keys = _referenced_parent_keys(plan)
    keys_by_table: dict[tuple[str, tuple[str, ...]], set[tuple[str, ...]]] = {}
    relationship_counts: dict[
        tuple[str, tuple[str, ...], str, tuple[str, ...]],
        Counter[tuple[str, ...]],
    ] = {}

    for table in plan.tables:
        artifact = table_artifacts.get(table.table_name)
        if artifact is None:
            issues.append(_issue("missing_artifact", "table artifact is missing", table.table_name))
            continue

        issues.extend(_validate_artifact_paths(plan, artifact))
        if artifact.csv_path is not None and artifact.csv_path.exists():
            # CSV is the validation source of truth today because it is the common
            # tabular artifact and can be streamed with low memory.
            table_keys, table_issues = _validate_csv_artifact(
                table,
                artifact.csv_path,
                keys_by_table,
                relationship_counts,
                should_keep_primary_keys=(
                    table.table_name,
                    _primary_key_columns(table),
                )
                in referenced_keys,
            )
            keys_by_table.update(table_keys)
            issues.extend(table_issues)

    return ValidationReport(
        passed=not issues,
        issues=tuple(issues),
        checked_tables=tuple(table.table_name for table in plan.tables),
        relationship_metrics=_relationship_metrics(plan, keys_by_table, relationship_counts),
    )


def _validate_artifact_paths(
    plan: GenerationPlan,
    artifact: TableArtifact,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if artifact.row_count != plan.table_plan(artifact.table_name).row_count:
        issues.append(
            _issue(
                "manifest_row_count_mismatch",
                f"manifest row count {artifact.row_count} does not match plan",
                artifact.table_name,
            )
        )
    if artifact.csv_path is not None and not artifact.csv_path.exists():
        issues.append(_issue("missing_csv", "CSV artifact is missing", artifact.table_name))
    if artifact.json_path is not None and not artifact.json_path.exists():
        issues.append(_issue("missing_json", "JSON artifact is missing", artifact.table_name))
    if artifact.sql_path is not None and not artifact.sql_path.exists():
        issues.append(_issue("missing_sql", "SQL artifact is missing", artifact.table_name))
    return issues


def _validate_csv_artifact(
    table: TablePlan,
    path: Path,
    keys_by_table: dict[tuple[str, tuple[str, ...]], set[tuple[str, ...]]],
    relationship_counts: dict[
        tuple[str, tuple[str, ...], str, tuple[str, ...]],
        Counter[tuple[str, ...]],
    ],
    *,
    should_keep_primary_keys: bool,
) -> tuple[dict[tuple[str, tuple[str, ...]], set[tuple[str, ...]]], list[ValidationIssue]]:
    """Validate one CSV table and return keys needed by later child tables."""

    issues: list[ValidationIssue] = []
    required_columns = tuple(
        column.name
        for column in table.columns
        if not column.nullable and column.strategy != ColumnStrategy.DEFAULT
    )
    primary_key_columns = _primary_key_columns(table)
    seen_primary_keys: set[tuple[str, ...]] = set()
    row_count = 0

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            row_count = index
            for column_name in required_columns:
                if row.get(column_name, "") == "":
                    issues.append(
                        _issue(
                            "required_value_missing",
                            f"row {index} is missing required column {column_name}",
                            table.table_name,
                        )
                    )

            if primary_key_columns:
                primary_key = tuple(row[column] for column in primary_key_columns)
                if primary_key in seen_primary_keys:
                    issues.append(
                        _issue(
                            "duplicate_primary_key",
                            f"duplicate primary key {primary_key}",
                            table.table_name,
                        )
                    )
                seen_primary_keys.add(primary_key)

            issues.extend(
                _validate_row_foreign_keys(
                    table,
                    row,
                    index,
                    keys_by_table,
                    relationship_counts,
                )
            )

    if row_count != table.row_count:
        issues.append(
            _issue(
                "csv_row_count_mismatch",
                f"CSV row count {row_count} does not match plan row count {table.row_count}",
                table.table_name,
            )
        )

    table_keys = {}
    if primary_key_columns and should_keep_primary_keys:
        table_keys[(table.table_name, primary_key_columns)] = seen_primary_keys
    return table_keys, issues


def _validate_row_foreign_keys(
    table: TablePlan,
    row: dict[str, str],
    row_index: int,
    keys_by_table: dict[tuple[str, tuple[str, ...]], set[tuple[str, ...]]],
    relationship_counts: dict[
        tuple[str, tuple[str, ...], str, tuple[str, ...]],
        Counter[tuple[str, ...]],
    ],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for source in _foreign_key_sources(table):
        valid_parent_keys = keys_by_table.get(
            (source.parent_table, source.parent_columns),
            set(),
        )
        child_key = tuple(row[column] for column in source.child_columns)
        relationship_key = (
            table.table_name,
            source.child_columns,
            source.parent_table,
            source.parent_columns,
        )
        relationship_counts.setdefault(relationship_key, Counter())[child_key] += 1
        if child_key not in valid_parent_keys:
            issues.append(
                _issue(
                    "foreign_key_missing_parent",
                    f"row {row_index} references missing parent key {child_key}",
                    table.table_name,
                )
            )
    return issues


def _relationship_metrics(
    plan: GenerationPlan,
    keys_by_table: dict[tuple[str, tuple[str, ...]], set[tuple[str, ...]]],
    relationship_counts: dict[
        tuple[str, tuple[str, ...], str, tuple[str, ...]],
        Counter[tuple[str, ...]],
    ],
) -> tuple[RelationshipFanoutMetric, ...]:
    """Summarize generated child distribution for each foreign-key relationship."""

    metrics: list[RelationshipFanoutMetric] = []
    for table in plan.tables:
        for source in _foreign_key_sources(table):
            metric_key = (
                table.table_name,
                source.child_columns,
                source.parent_table,
                source.parent_columns,
            )
            counts = relationship_counts.get(metric_key)
            parent_keys = keys_by_table.get((source.parent_table, source.parent_columns))
            if counts is None or parent_keys is None:
                continue

            child_row_count = sum(counts.values())
            parent_key_count = len(parent_keys)
            children_per_parent = [counts.get(parent_key, 0) for parent_key in parent_keys]
            metrics.append(
                RelationshipFanoutMetric(
                    child_table=table.table_name,
                    child_columns=source.child_columns,
                    parent_table=source.parent_table,
                    parent_columns=source.parent_columns,
                    parent_key_count=parent_key_count,
                    child_row_count=child_row_count,
                    min_children_per_parent=(
                        min(children_per_parent) if children_per_parent else 0
                    ),
                    max_children_per_parent=(
                        max(children_per_parent) if children_per_parent else 0
                    ),
                    average_children_per_parent=(
                        child_row_count / parent_key_count if parent_key_count else 0.0
                    ),
                    empty_parent_count=sum(1 for count in children_per_parent if count == 0),
                )
            )
    return tuple(metrics)


def _referenced_parent_keys(
    plan: GenerationPlan,
) -> set[tuple[str, tuple[str, ...]]]:
    return {
        (source.parent_table, source.parent_columns)
        for table in plan.tables
        for source in _foreign_key_sources(table)
    }


def _primary_key_columns(table: TablePlan) -> tuple[str, ...]:
    return tuple(
        column.name for column in table.columns if column.strategy == ColumnStrategy.PRIMARY_KEY
    )


def _foreign_key_sources(table: TablePlan):
    seen = set()
    for column in table.columns:
        source = column.foreign_key_source
        if source is None:
            continue
        key = (source.parent_table, source.child_columns, source.parent_columns)
        if key in seen:
            continue
        seen.add(key)
        yield source


def _issue(code: str, message: str, table_name: str | None = None) -> ValidationIssue:
    return ValidationIssue(code=code, message=message, table_name=table_name)
