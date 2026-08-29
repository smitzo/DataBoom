"""Run the 1M-record relational generation benchmark."""

from __future__ import annotations

import argparse
import time
import tracemalloc
from pathlib import Path

from common import directory_size, prepare_output_dir, write_metrics

from databoom.export import ArtifactExporter
from databoom.generation import OutputFormat, create_generation_plan
from databoom.ingest import parse_postgres_ddl
from databoom.validation import validate_export

DDL = """
CREATE TABLE customers (
    id bigint PRIMARY KEY,
    full_name text NOT NULL,
    email text NOT NULL,
    segment text NOT NULL,
    created_at timestamp NOT NULL
);

CREATE TABLE products (
    id bigint PRIMARY KEY,
    sku text NOT NULL,
    name text NOT NULL,
    price numeric(12, 2) NOT NULL
);

CREATE TABLE orders (
    id bigint PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES customers(id),
    status text NOT NULL,
    total numeric(12, 2) NOT NULL,
    created_at timestamp NOT NULL
);

CREATE TABLE order_items (
    id bigint PRIMARY KEY,
    order_id bigint NOT NULL REFERENCES orders(id),
    product_id bigint NOT NULL REFERENCES products(id),
    quantity bigint NOT NULL,
    unit_price numeric(12, 2) NOT NULL
);

CREATE TABLE payments (
    id bigint PRIMARY KEY,
    order_id bigint NOT NULL REFERENCES orders(id),
    amount numeric(12, 2) NOT NULL,
    status text NOT NULL,
    created_at timestamp NOT NULL
);
"""

BASE_ROW_COUNTS = {
    "customers": 100_000,
    "products": 20_000,
    "orders": 250_000,
    "order_items": 500_000,
    "payments": 130_000,
}

DEFAULT_FORMATS = (OutputFormat.CSV,)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/benchmarks/relational_1m"),
    )
    parser.add_argument("--seed", default="relational-1m")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--scale",
        type=_positive_float,
        default=1.0,
        help="Scale row counts for smoke tests. Official benchmark uses 1.0.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Measure export only. Validation should stay enabled for official numbers.",
    )
    args = parser.parse_args()

    row_counts = scaled_row_counts(args.scale)
    prepare_output_dir(args.output_dir, overwrite=args.overwrite)

    tracemalloc.start()
    total_started_at = time.perf_counter()

    parse_started_at = time.perf_counter()
    database = parse_postgres_ddl(DDL)
    parse_seconds = time.perf_counter() - parse_started_at

    plan_started_at = time.perf_counter()
    plan = create_generation_plan(
        database,
        row_counts=row_counts,
        seed=args.seed,
        output_formats=DEFAULT_FORMATS,
    )
    plan_seconds = time.perf_counter() - plan_started_at

    export_started_at = time.perf_counter()
    manifest = ArtifactExporter(plan, args.output_dir).export()
    export_seconds = time.perf_counter() - export_started_at

    validation_seconds = 0.0
    validation_passed = None
    issues = []
    if not args.skip_validation:
        validation_started_at = time.perf_counter()
        report = validate_export(plan, manifest)
        validation_seconds = time.perf_counter() - validation_started_at
        validation_passed = report.passed
        issues = [issue.to_dict() for issue in report.issues]

    total_seconds = time.perf_counter() - total_started_at
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    metrics = {
        "phase": "relational_1m",
        "scale": args.scale,
        "official_scale": args.scale == 1.0,
        "records": plan.total_rows,
        "tables": len(plan.tables),
        "row_counts": row_counts,
        "output_formats": [output_format.value for output_format in DEFAULT_FORMATS],
        "parse_seconds": round(parse_seconds, 3),
        "plan_seconds": round(plan_seconds, 3),
        "export_seconds": round(export_seconds, 3),
        "validation_seconds": round(validation_seconds, 3),
        "elapsed_seconds": round(total_seconds, 3),
        "records_per_second": round(plan.total_rows / total_seconds, 3),
        "peak_memory_mb": round(peak_bytes / 1024 / 1024, 3),
        "artifact_size_mb": round(directory_size(args.output_dir) / 1024 / 1024, 3),
        "validation_passed": validation_passed,
        "issues": issues,
        "output_dir": str(args.output_dir),
    }
    write_metrics(args.output_dir, metrics)

    if validation_passed is False:
        raise SystemExit(1)


def scaled_row_counts(scale: float) -> dict[str, int]:
    """Return row counts scaled from the official 1M benchmark shape."""

    return {
        table_name: max(1, round(row_count * scale))
        for table_name, row_count in BASE_ROW_COUNTS.items()
    }


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("scale must be greater than zero")
    return parsed


if __name__ == "__main__":
    main()
