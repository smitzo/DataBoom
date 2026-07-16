import csv
import json

from boom_data.export import ArtifactExporter
from boom_data.generation import OutputFormat, create_generation_plan
from boom_data.ingest import parse_postgres_ddl


def test_artifact_exporter_writes_csv_sql_and_manifest(tmp_path) -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (
            id bigint PRIMARY KEY,
            name text NOT NULL
        );
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES accounts(id),
            email text NOT NULL
        );
        """
    )
    plan = create_generation_plan(
        database,
        row_counts={"accounts": 2, "users": 3},
        seed=42,
        output_formats=(OutputFormat.CSV, OutputFormat.SQL),
    )

    manifest = ArtifactExporter(plan, tmp_path).export()

    assert manifest.manifest_path.exists()
    assert {table.table_name: table.row_count for table in manifest.tables} == {
        "public.accounts": 2,
        "public.users": 3,
    }

    users_csv = tmp_path / "public__users.csv"
    users_sql = tmp_path / "public__users.sql"

    with users_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 3
    assert {row["account_id"] for row in rows} <= {"1", "2"}
    assert 'INSERT INTO "public"."users"' in users_sql.read_text(encoding="utf-8")

    manifest_data = json.loads(manifest.manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["tables"][1]["csv_path"].endswith("public__users.csv")


def test_artifact_exporter_writes_empty_table_headers(tmp_path) -> None:
    database = parse_postgres_ddl("CREATE TABLE users (id bigint PRIMARY KEY, email text);")
    plan = create_generation_plan(database, row_counts={"users": 0}, seed=42)

    ArtifactExporter(plan, tmp_path).export()

    assert (tmp_path / "public__users.csv").read_text(encoding="utf-8") == "id,email\n"
