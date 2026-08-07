"""Run the Phase 2 500k-record generation benchmark."""

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
    status text NOT NULL,
    created_at timestamp NOT NULL
);

CREATE TABLE accounts (
    id bigint PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES customers(id),
    account_number text NOT NULL,
    status text NOT NULL,
    opened_at timestamp NOT NULL
);

CREATE TABLE cards (
    id bigint PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES accounts(id),
    card_token text NOT NULL,
    status text NOT NULL,
    issued_at timestamp NOT NULL
);

CREATE TABLE transactions (
    id bigint PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES accounts(id),
    amount numeric(12, 2) NOT NULL,
    status text NOT NULL,
    created_at timestamp NOT NULL
);

CREATE TABLE alerts (
    id bigint PRIMARY KEY,
    transaction_id bigint NOT NULL REFERENCES transactions(id),
    alert_type text NOT NULL,
    severity text NOT NULL,
    created_at timestamp NOT NULL
);
"""

ROW_COUNTS = {
    "customers": 50_000,
    "accounts": 75_000,
    "cards": 75_000,
    "transactions": 225_000,
    "alerts": 75_000,
}

DEFAULT_FORMATS = (OutputFormat.CSV,)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/benchmarks/phase2_500k"),
    )
    parser.add_argument("--seed", default="phase2-500k")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Measure export only. Validation should stay enabled for official numbers.",
    )
    args = parser.parse_args()

    prepare_output_dir(args.output_dir, overwrite=args.overwrite)

    tracemalloc.start()
    total_started_at = time.perf_counter()

    parse_started_at = time.perf_counter()
    database = parse_postgres_ddl(DDL)
    parse_seconds = time.perf_counter() - parse_started_at

    plan_started_at = time.perf_counter()
    plan = create_generation_plan(
        database,
        row_counts=ROW_COUNTS,
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
        "phase": "phase2_500k",
        "records": plan.total_rows,
        "tables": len(plan.tables),
        "row_counts": ROW_COUNTS,
        "output_formats": [output_format.value for output_format in DEFAULT_FORMATS],
        "parse_seconds": round(parse_seconds, 3),
        "plan_seconds": round(plan_seconds, 3),
        "export_seconds": round(export_seconds, 3),
        "validation_seconds": round(validation_seconds, 3),
        "elapsed_seconds": round(total_seconds, 3),
        "peak_memory_mb": round(peak_bytes / 1024 / 1024, 3),
        "artifact_size_mb": round(directory_size(args.output_dir) / 1024 / 1024, 3),
        "validation_passed": validation_passed,
        "issues": issues,
        "output_dir": str(args.output_dir),
    }
    write_metrics(args.output_dir, metrics)

    if validation_passed is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
