"""Run the Phase 1 100k-record generation benchmark."""

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
CREATE TABLE accounts (
    id bigint PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE users (
    id bigint PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES accounts(id),
    email text NOT NULL,
    created_at timestamp NOT NULL
);

CREATE TABLE orders (
    id bigint PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES users(id),
    amount numeric(10, 2) NOT NULL,
    status text NOT NULL,
    created_at timestamp NOT NULL
);
"""

ROW_COUNTS = {
    "accounts": 1_000,
    "users": 24_000,
    "orders": 75_000,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/benchmarks/phase1_100k"),
    )
    parser.add_argument("--seed", default="phase1-100k")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    prepare_output_dir(args.output_dir, overwrite=args.overwrite)

    tracemalloc.start()
    started_at = time.perf_counter()

    database = parse_postgres_ddl(DDL)
    plan = create_generation_plan(
        database,
        row_counts=ROW_COUNTS,
        seed=args.seed,
        output_formats=(OutputFormat.CSV,),
    )
    manifest = ArtifactExporter(plan, args.output_dir).export()
    report = validate_export(plan, manifest)

    elapsed_seconds = time.perf_counter() - started_at
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    metrics = {
        "records": plan.total_rows,
        "tables": len(plan.tables),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "peak_memory_mb": round(peak_bytes / 1024 / 1024, 3),
        "artifact_size_mb": round(directory_size(args.output_dir) / 1024 / 1024, 3),
        "validation_passed": report.passed,
        "issues": [issue.to_dict() for issue in report.issues],
        "output_dir": str(args.output_dir),
    }
    write_metrics(args.output_dir, metrics)

    if not report.passed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
