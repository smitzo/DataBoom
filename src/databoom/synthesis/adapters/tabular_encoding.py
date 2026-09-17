"""Reversible mixed-type encoding shared by optional ML worker adapters.

This module is safe to import without NumPy. Worker adapters pass their lazily
imported NumPy module into the functions that need it.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from databoom.synthesis.contracts import ColumnKind, DatasetContract, JsonScalar

_NULL_TOKEN = "__DATABOOM_NULL__"


def encode_csv(
    path: Path,
    dataset: DatasetContract,
    numpy: Any,
) -> tuple[Any, dict[str, dict[str, JsonScalar]]]:
    """Read a reviewed CSV into a bounded numeric matrix and transform metadata."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = tuple(reader.fieldnames or ())
        if actual != dataset.column_names:
            raise ValueError(
                "CSV columns must exactly match the reviewed dataset contract in order: "
                f"expected {dataset.column_names}, received {actual}"
            )
        rows = list(reader)
    if not rows:
        raise ValueError("training partition is empty")

    encoded_columns: list[Any] = []
    metadata: dict[str, dict[str, JsonScalar]] = {}
    offset = 0
    for column in dataset.columns:
        raw_values = [row[column.name] for row in rows]
        if column.kind == ColumnKind.DISCRETE:
            normalized = [value if value != "" else _NULL_TOKEN for value in raw_values]
            if not column.nullable and _NULL_TOKEN in normalized:
                raise ValueError(f"non-nullable column contains null values: {column.name}")
            observed = {value for value in normalized if value != _NULL_TOKEN}
            sentinel = _unique_null_token(observed)
            normalized = [sentinel if value == _NULL_TOKEN else value for value in normalized]
            categories = sorted(set(normalized))
            category_index = {value: index for index, value in enumerate(categories)}
            values = numpy.zeros((len(rows), len(categories)), dtype="float32")
            values[
                numpy.arange(len(rows)),
                [category_index[value] for value in normalized],
            ] = 1.0
            encoded_columns.append(values)
            metadata[column.name] = {
                "kind": "discrete",
                "start": offset,
                "end": offset + len(categories),
                "categories_json": json.dumps(categories, ensure_ascii=False),
                "null_sentinel": sentinel,
            }
            offset += len(categories)
            continue

        parsed: list[float | None] = []
        observed_numeric: list[float] = []
        for value in raw_values:
            if value == "":
                if not column.nullable:
                    raise ValueError(f"non-nullable column contains null values: {column.name}")
                parsed.append(None)
                continue
            try:
                number = float(value)
            except ValueError as exc:
                raise ValueError(f"continuous column is not numeric: {column.name}") from exc
            if not math.isfinite(number):
                raise ValueError(f"continuous column contains a non-finite value: {column.name}")
            parsed.append(number)
            observed_numeric.append(number)
        if not observed_numeric:
            raise ValueError(f"continuous column contains no numeric values: {column.name}")

        minimum = min(observed_numeric)
        maximum = max(observed_numeric)
        ordered = sorted(observed_numeric)
        middle = len(ordered) // 2
        median = (
            ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
        )
        scale = maximum - minimum
        denominator = scale if scale > 0 else 1.0
        filled = [median if value is None else value for value in parsed]
        values = numpy.asarray(
            [[(value - minimum) / denominator] for value in filled],
            dtype="float32",
        )
        encoded_columns.append(values)
        settings: dict[str, JsonScalar] = {
            "kind": "continuous",
            "value_index": offset,
            "minimum": minimum,
            "maximum": maximum,
            "imputation_value": median,
        }
        offset += 1
        if column.nullable:
            missing = numpy.asarray(
                [[1.0 if value is None else 0.0] for value in parsed],
                dtype="float32",
            )
            encoded_columns.append(missing)
            settings["null_index"] = offset
            offset += 1
        metadata[column.name] = settings

    matrix = numpy.concatenate(encoded_columns, axis=1)
    if matrix.shape[1] > 512:
        raise ValueError("encoded feature count exceeds the experimental limit of 512")
    return matrix, metadata


def decode_rows(
    encoded: Any,
    dataset: DatasetContract,
    metadata: dict[str, dict[str, Any]],
    numpy: Any,
) -> list[dict[str, str]]:
    """Restore encoded samples to the reviewed CSV contract."""

    values = numpy.asarray(encoded, dtype="float64")
    if values.ndim != 2:
        raise ValueError("encoded samples must be a two-dimensional matrix")
    if not numpy.isfinite(values).all():
        raise ValueError("encoded samples contain non-finite values")

    result: list[dict[str, str]] = []
    for row in values:
        output: dict[str, str] = {}
        for column in dataset.columns:
            settings = metadata[column.name]
            if settings["kind"] == "discrete":
                start = int(settings["start"])
                end = int(settings["end"])
                categories = json.loads(str(settings["categories_json"]))
                category = categories[int(numpy.argmax(row[start:end]))]
                output[column.name] = "" if category == settings["null_sentinel"] else str(category)
                continue

            null_index = settings.get("null_index")
            if null_index is not None and row[int(null_index)] >= 0.5:
                output[column.name] = ""
                continue
            minimum = float(settings["minimum"])
            maximum = float(settings["maximum"])
            normalized = min(1.0, max(0.0, float(row[int(settings["value_index"])])))
            restored = minimum + normalized * (maximum - minimum)
            output[column.name] = format(restored, ".15g")
        result.append(output)
    return result


def write_rows(path: Path, dataset: DatasetContract, rows: list[dict[str, str]]) -> None:
    """Atomically write decoded rows to a CSV artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=dataset.column_names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def _unique_null_token(observed: set[str]) -> str:
    candidate = _NULL_TOKEN
    suffix = 1
    while candidate in observed:
        candidate = f"{_NULL_TOKEN}_{suffix}"
        suffix += 1
    return candidate
