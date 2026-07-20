"""Local filesystem exporters for generated rows."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from boom_data.generation import GeneratedRow, OutputFormat, RowGenerator
from boom_data.generation.plan import GenerationPlan, TablePlan


@dataclass(frozen=True)
class TableArtifact:
    """Artifact paths and row count for one generated table."""

    table_name: str
    row_count: int
    csv_path: Path | None = None
    json_path: Path | None = None
    sql_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "row_count": self.row_count,
            "csv_path": str(self.csv_path) if self.csv_path else None,
            "json_path": str(self.json_path) if self.json_path else None,
            "sql_path": str(self.sql_path) if self.sql_path else None,
        }


@dataclass(frozen=True)
class ExportManifest:
    """Manifest for a local artifact export run."""

    output_dir: Path
    manifest_path: Path
    tables: tuple[TableArtifact, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "tables": [table.to_dict() for table in self.tables],
        }


class ArtifactExporter:
    """Stream a generation plan to local CSV and SQL artifacts."""

    def __init__(self, plan: GenerationPlan, output_dir: Path) -> None:
        self.plan = plan
        self.output_dir = output_dir

    def export(self) -> ExportManifest:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        row_generator = RowGenerator.from_plan(self.plan)
        table_artifacts = tuple(
            self._export_table(row_generator, table)
            for table in self.plan.tables
        )
        manifest = ExportManifest(
            output_dir=self.output_dir,
            manifest_path=self.output_dir / "manifest.json",
            tables=table_artifacts,
        )
        manifest.manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        return manifest

    def _export_table(self, row_generator: RowGenerator, table: TablePlan) -> TableArtifact:
        csv_writer = None
        json_writer = None
        sql_writer = None

        if OutputFormat.CSV in self.plan.output_formats:
            csv_writer = _CsvTableWriter(
                self.output_dir / f"{_safe_filename(table.table_name)}.csv",
                table,
            )
        if OutputFormat.JSON in self.plan.output_formats:
            json_writer = _JsonTableWriter(
                self.output_dir / f"{_safe_filename(table.table_name)}.json",
            )
        if OutputFormat.SQL in self.plan.output_formats:
            sql_writer = _SqlTableWriter(
                self.output_dir / f"{_safe_filename(table.table_name)}.sql",
                table,
            )

        row_count = 0
        with _close_writers(csv_writer, json_writer, sql_writer):
            for row in row_generator.iter_table_rows(table):
                row_count += 1
                if csv_writer is not None:
                    csv_writer.write(row)
                if json_writer is not None:
                    json_writer.write(row)
                if sql_writer is not None:
                    sql_writer.write(row)

        return TableArtifact(
            table_name=table.table_name,
            row_count=row_count,
            csv_path=csv_writer.path if csv_writer is not None else None,
            json_path=json_writer.path if json_writer is not None else None,
            sql_path=sql_writer.path if sql_writer is not None else None,
        )


class _close_writers:
    def __init__(self, *writers) -> None:
        self.writers = writers

    def __enter__(self) -> None:
        return None

    def __exit__(self, *args) -> None:
        for writer in self.writers:
            if writer is not None:
                writer.close()


class _CsvTableWriter:
    def __init__(self, path: Path, table: TablePlan) -> None:
        self.path = path
        self.headers = tuple(column.name for column in table.columns)
        self.handle = path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.handle, fieldnames=self.headers)
        self.writer.writeheader()

    def write(self, row: GeneratedRow) -> None:
        self.writer.writerow({key: _csv_value(row[key]) for key in self.headers})

    def close(self) -> None:
        self.handle.close()


class _SqlTableWriter:
    def __init__(self, path: Path, table: TablePlan) -> None:
        self.path = path
        self.table = table
        self.headers = tuple(column.name for column in table.columns)
        self.handle: TextIO = path.open("w", encoding="utf-8")

    def write(self, row: GeneratedRow) -> None:
        columns = ", ".join(_quote_identifier(column) for column in self.headers)
        values = ", ".join(_sql_value(row[column]) for column in self.headers)
        self.handle.write(
            f"INSERT INTO {_quote_table(self.table.table_name)} "
            f"({columns}) VALUES ({values});\n"
        )

    def close(self) -> None:
        self.handle.close()


class _JsonTableWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = path.open("w", encoding="utf-8")
        self.first_row = True
        self.handle.write("[\n")

    def write(self, row: GeneratedRow) -> None:
        if not self.first_row:
            self.handle.write(",\n")
        self.first_row = False
        self.handle.write(json.dumps({key: _json_value(value) for key, value in row.items()}))

    def close(self) -> None:
        self.handle.write("\n]\n")
        self.handle.close()


def _csv_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return value


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _sql_value(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, datetime):
        return _quote_literal(value.isoformat())
    if isinstance(value, dict):
        return _quote_literal(json.dumps(value, separators=(",", ":"), sort_keys=True))
    return _quote_literal(str(value))


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _quote_table(table_name: str) -> str:
    return ".".join(_quote_identifier(part) for part in table_name.split("."))


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _safe_filename(value: str) -> str:
    return value.replace(".", "__").replace("/", "_")
