from databoom.export import ArtifactExporter
from databoom.generation import OutputFormat, create_generation_plan
from databoom.ingest import parse_postgres_ddl
from databoom.validation import validate_export


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
    assert len(report.relationship_metrics) == 1
    metric = report.relationship_metrics[0]
    assert metric.child_table == "public.users"
    assert metric.child_columns == ("account_id",)
    assert metric.parent_table == "public.accounts"
    assert metric.parent_columns == ("id",)
    assert metric.parent_key_count == 2
    assert metric.child_row_count == 3
    assert metric.min_children_per_parent == 1
    assert metric.max_children_per_parent == 2
    assert metric.average_children_per_parent == 1.5
    assert metric.empty_parent_count == 0


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


def test_validate_export_detects_required_and_primary_key_errors(tmp_path) -> None:
    database = parse_postgres_ddl(
        "CREATE TABLE users (id bigint PRIMARY KEY, email text NOT NULL);"
    )
    plan = create_generation_plan(
        database,
        row_counts={"users": 2},
        seed=42,
        output_formats=(OutputFormat.CSV,),
    )
    manifest = ArtifactExporter(plan, tmp_path).export()
    users_csv = tmp_path / "public__users.csv"
    users_csv.write_text("id,email\n1,\n1,user@example.com\n", encoding="utf-8")

    report = validate_export(plan, manifest)

    assert report.passed is False
    assert {issue.code for issue in report.issues} == {
        "required_value_missing",
        "duplicate_primary_key",
    }


def test_validate_export_writes_json_report(tmp_path) -> None:
    database = parse_postgres_ddl("CREATE TABLE users (id bigint PRIMARY KEY);")
    plan = create_generation_plan(database, row_counts={"users": 1}, seed=42)
    manifest = ArtifactExporter(plan, tmp_path).export()
    report = validate_export(plan, manifest)
    report_path = tmp_path / "validation.json"

    report.write_json(report_path)
    payload = report_path.read_text(encoding="utf-8")

    assert '"passed": true' in payload
    assert '"relationship_metrics": []' in payload


def test_validate_export_reports_empty_parent_fanout(tmp_path) -> None:
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
        row_counts={"accounts": 3, "users": 2},
        seed=42,
        output_formats=(OutputFormat.CSV,),
    )
    manifest = ArtifactExporter(plan, tmp_path).export()

    report = validate_export(plan, manifest)

    assert report.passed is True
    assert report.relationship_metrics[0].empty_parent_count == 1
    assert report.relationship_metrics[0].min_children_per_parent == 0
    assert report.relationship_metrics[0].max_children_per_parent == 1
