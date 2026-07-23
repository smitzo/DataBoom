"""Validation for local generated artifacts."""

from __future__ import annotations

import csv
import json
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
class ValidationReport:
    """Machine-readable validation result."""

    passed: bool
    issues: tuple[ValidationIssue, ...]
    checked_tables: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checked_tables": list(self.checked_tables),
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def write_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def validate_export(plan: GenerationPlan, manifest: ExportManifest) -> ValidationReport:
    """Validate local artifacts against a generation plan."""

    issues: list[ValidationIssue] = []
    table_artifacts = {artifact.table_name: artifact for artifact in manifest.tables}
    rows_by_table: dict[str, list[dict[str, str]]] = {}

    for table in plan.tables:
        artifact = table_artifacts.get(table.table_name)
        if artifact is None:
            issues.append(_issue("missing_artifact", "table artifact is missing", table.table_name))
            continue

        issues.extend(_validate_artifact_paths(plan, artifact))
        if artifact.csv_path is not None and artifact.csv_path.exists():
            rows = _read_csv_rows(artifact.csv_path)
            rows_by_table[table.table_name] = rows
            issues.extend(_validate_csv_rows(table, rows))

    issues.extend(_validate_foreign_keys(plan, rows_by_table))
    return ValidationReport(
        passed=not issues,
        issues=tuple(issues),
        checked_tables=tuple(table.table_name for table in plan.tables),
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


def _validate_csv_rows(table: TablePlan, rows: list[dict[str, str]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if len(rows) != table.row_count:
        issues.append(
            _issue(
                "csv_row_count_mismatch",
                f"CSV row count {len(rows)} does not match plan row count {table.row_count}",
                table.table_name,
            )
        )

    required_columns = tuple(
        column.name
        for column in table.columns
        if not column.nullable and column.strategy != ColumnStrategy.DEFAULT
    )
    primary_key_columns = tuple(
        column.name for column in table.columns if column.strategy == ColumnStrategy.PRIMARY_KEY
    )
    seen_primary_keys: set[tuple[str, ...]] = set()

    for index, row in enumerate(rows, start=1):
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

    return issues


def _validate_foreign_keys(
    plan: GenerationPlan,
    rows_by_table: dict[str, list[dict[str, str]]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    keys_by_table: dict[tuple[str, tuple[str, ...]], set[tuple[str, ...]]] = {}

    for table in plan.tables:
        rows = rows_by_table.get(table.table_name)
        if rows is None:
            continue
        primary_key_columns = tuple(
            column.name for column in table.columns if column.strategy == ColumnStrategy.PRIMARY_KEY
        )
        if primary_key_columns:
            keys_by_table[(table.table_name, primary_key_columns)] = {
                tuple(row[column] for column in primary_key_columns)
                for row in rows
            }

    for table in plan.tables:
        rows = rows_by_table.get(table.table_name)
        if rows is None:
            continue
        for source in _foreign_key_sources(table):
            valid_parent_keys = keys_by_table.get(
                (source.parent_table, source.parent_columns),
                set(),
            )
            for index, row in enumerate(rows, start=1):
                child_key = tuple(row[column] for column in source.child_columns)
                if child_key not in valid_parent_keys:
                    issues.append(
                        _issue(
                            "foreign_key_missing_parent",
                            f"row {index} references missing parent key {child_key}",
                            table.table_name,
                        )
                    )
    return issues


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


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _issue(code: str, message: str, table_name: str | None = None) -> ValidationIssue:
    return ValidationIssue(code=code, message=message, table_name=table_name)
