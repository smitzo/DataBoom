"""Run the Phase 1 100k-record generation benchmark."""

from __future__ import annotations

import argparse
import json
import shutil
import time
import tracemalloc
from pathlib import Path

from boom_data.export import ArtifactExporter
from boom_data.generation import OutputFormat, create_generation_plan
from boom_data.ingest import parse_postgres_ddl
from boom_data.validation import validate_export

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

    if args.output_dir.exists() and args.overwrite:
        shutil.rmtree(args.output_dir)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"output directory is not empty: {args.output_dir}")

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
        "artifact_size_mb": round(_directory_size(args.output_dir) / 1024 / 1024, 3),
        "validation_passed": report.passed,
        "issues": [issue.to_dict() for issue in report.issues],
        "output_dir": str(args.output_dir),
    }
    metrics_path = args.output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))

    if not report.passed:
        raise SystemExit(1)


def _directory_size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


if __name__ == "__main__":
    main()
