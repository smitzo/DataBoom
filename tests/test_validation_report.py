from boom_data.export import ArtifactExporter
from boom_data.generation import OutputFormat, create_generation_plan
from boom_data.ingest import parse_postgres_ddl
from boom_data.validation import validate_export


def test_validate_export_passes_for_generated_artifacts(tmp_path) -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (id bigint PRIMARY KEY, name text NOT NULL);
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
        output_formats=(OutputFormat.CSV, OutputFormat.JSON, OutputFormat.SQL),
    )
    manifest = ArtifactExporter(plan, tmp_path).export()

    report = validate_export(plan, manifest)

    assert report.passed is True
    assert report.issues == ()


def test_validate_export_detects_broken_foreign_key(tmp_path) -> None:
    database = parse_postgres_ddl(
        """
        CREATE TABLE accounts (id bigint PRIMARY KEY);
        CREATE TABLE users (
            id bigint PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES accounts(id)
        );
        """
    )
    plan = create_generation_plan(
        database,
        row_counts={"accounts": 1, "users": 1},
        seed=42,
        output_formats=(OutputFormat.CSV,),
    )
    manifest = ArtifactExporter(plan, tmp_path).export()
    users_csv = tmp_path / "public__users.csv"
    users_csv.write_text("id,account_id\n1,999\n", encoding="utf-8")

    report = validate_export(plan, manifest)

    assert report.passed is False
    assert report.issues[0].code == "foreign_key_missing_parent"


def test_validate_export_writes_json_report(tmp_path) -> None:
    database = parse_postgres_ddl("CREATE TABLE users (id bigint PRIMARY KEY);")
    plan = create_generation_plan(database, row_counts={"users": 1}, seed=42)
    manifest = ArtifactExporter(plan, tmp_path).export()
    report = validate_export(plan, manifest)
    report_path = tmp_path / "validation.json"

    report.write_json(report_path)

    assert '"passed": true' in report_path.read_text(encoding="utf-8")
