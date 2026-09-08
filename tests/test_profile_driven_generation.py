from datetime import datetime

from databoom.generation import (
    ColumnProfileHint,
    OutputFormat,
    RowGenerator,
    TopValueHint,
    create_generation_plan,
)
from databoom.ingest import parse_postgres_ddl


def test_row_generation_respects_profile_value_hints() -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE customers (
            id bigint PRIMARY KEY,
            status text NOT NULL,
            amount numeric NOT NULL,
            seen_at timestamp NOT NULL,
            nickname text
        );
        """
    )
    plan = create_generation_plan(
        database,
        row_counts={"customers": 100},
        seed=42,
        output_formats=(OutputFormat.CSV,),
        column_hints=(
            ColumnProfileHint(
                table_name="public.customers",
                column_name="status",
                sample_count=100,
                null_rate=0.0,
                distinct_count=2,
                top_values=(
                    TopValueHint(value="active", count=75),
                    TopValueHint(value="inactive", count=25),
                ),
            ),
            ColumnProfileHint(
                table_name="public.customers",
                column_name="amount",
                sample_count=100,
                null_rate=0.0,
                distinct_count=90,
                min_value="10.50",
                max_value="20.75",
            ),
            ColumnProfileHint(
                table_name="public.customers",
                column_name="seen_at",
                sample_count=100,
                null_rate=0.0,
                distinct_count=100,
                min_value="2024-01-01T00:00:00Z",
                max_value="2024-01-31T00:00:00Z",
            ),
            ColumnProfileHint(
                table_name="public.customers",
                column_name="nickname",
                sample_count=100,
                null_rate=1.0,
                distinct_count=0,
            ),
        ),
    )

    rows = [record.row for record in RowGenerator.from_plan(plan).iter_records()]
    statuses = [row["status"] for row in rows]
    amounts = [row["amount"] for row in rows]
    seen_at_values = [row["seen_at"] for row in rows]
    minimum_datetime = datetime.fromisoformat("2024-01-01T00:00:00+00:00")
    maximum_datetime = datetime.fromisoformat("2024-01-31T00:00:00+00:00")

    assert len(rows) == 100
    assert set(statuses) == {"active", "inactive"}
    assert statuses.count("active") > statuses.count("inactive")
    assert all(10.50 <= amount <= 20.75 for amount in amounts)
    assert all(minimum_datetime <= value <= maximum_datetime for value in seen_at_values)
    assert all(row["nickname"] is None for row in rows)
