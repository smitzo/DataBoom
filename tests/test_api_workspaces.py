from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from databoom.api import create_app
from databoom.core.config import Settings
from databoom.profiling import (
    ChildCountFrequency,
    ColumnProfile,
    ConnectionTest,
    RelationshipProfile,
    SourceProfile,
    TableProfile,
    TopValue,
)
from databoom.schema import (
    ColumnSchema,
    DatabaseSchema,
    ForeignKeyConstraint,
    PostgresType,
    PrimaryKeyConstraint,
    TableSchema,
    UniqueConstraint,
)
from databoom.schema.models import TypeFamily


def test_workspace_sources_are_grouped_by_product(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))

    response = client.get("/workspace-sources")
    table_sources = client.get("/products/table-boom/workspace-sources")
    doc_sources = client.get("/products/docu-boom/workspace-sources")

    assert response.status_code == 200
    assert table_sources.status_code == 200
    assert doc_sources.status_code == 200

    all_payload = response.json()
    table_payload = table_sources.json()
    doc_payload = doc_sources.json()

    assert {"table-boom", "docu-boom", "graph-boom", "masker-boom"} <= {
        source["product_id"] for source in all_payload
    }
    assert {source["product_id"] for source in table_payload} == {"table-boom"}
    assert {source["kind"] for source in table_payload} == {"relational"}
    assert {source["product_id"] for source in doc_payload} == {"docu-boom"}
    assert {source["kind"] for source in doc_payload} == {"document"}
    assert table_payload[0]["resources"][0]["resource_type"] == "table"
    assert doc_payload[0]["resources"][0]["resource_type"] == "collection"


def test_workspace_source_detail_returns_resources(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))

    response = client.get("/workspace-sources/commerce-store")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Commerce Store"
    assert payload["engine"] == "PostgreSQL"
    assert [resource["name"] for resource in payload["resources"]] == [
        "customers",
        "products",
        "orders",
        "order_items",
        "payments",
    ]


def test_product_run_rejects_incompatible_workspace_source(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "table-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    response = client.post(
        "/products/table-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {"customers": 2},
            "seed": "wrong-source",
            "output_formats": ["csv"],
            "source_id": "customer-events",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "workspace source is not compatible with this product"


def test_product_run_uses_selected_workspace_source_resources(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "table-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    response = client.post(
        "/products/table-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {"customers": 2, "bank_accounts": 3, "transactions": 4},
            "seed": "bank-source",
            "output_formats": ["csv", "sql"],
            "source_id": "core-banking",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert [table["table_name"] for table in payload["tables"]] == [
        "public.customers",
        "public.bank_accounts",
        "public.transactions",
    ]
    assert payload["total_rows"] == 9

    preview = client.get(
        f"/runs/{payload['run_id']}/preview",
        params={"table": "bank_accounts", "limit": 2},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["table_name"] == "public.bank_accounts"


def test_document_product_run_uses_selected_workspace_source_resources(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "docu-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    response = client.post(
        "/products/docu-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {"patients": 2, "clinical_notes": 3, "claims": 4},
            "seed": "clinical-source",
            "output_formats": ["json", "ndjson"],
            "source_id": "clinical-documents",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert [collection["collection_name"] for collection in payload["collections"]] == [
        "patients",
        "clinical_notes",
        "claims",
    ]
    assert payload["total_rows"] == 9

    preview = client.get(
        f"/runs/{payload['run_id']}/document-preview",
        params={"collection": "clinical_notes", "limit": 2},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["collection_name"] == "clinical_notes"


def test_workspace_source_can_be_created_for_a_product(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    response = client.post(
        "/workspace-sources",
        headers=_auth_headers(token),
        json={
            "id": "billing-ledger",
            "product_id": "table-boom",
            "kind": "relational",
            "name": "Billing Ledger",
            "engine": "PostgreSQL",
            "host": "billing.local",
            "description": "Tenant billing tables.",
            "resources": [
                {
                    "name": "invoices",
                    "resource_type": "table",
                    "estimated_rows": 12,
                    "columns": ["id", "customer_id", "amount", "status"],
                }
            ],
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["id"] == "billing-ledger"
    assert payload["resources"][0]["name"] == "invoices"

    product_sources = client.get("/products/table-boom/workspace-sources")
    assert product_sources.status_code == 200, product_sources.text
    assert "billing-ledger" in {source["id"] for source in product_sources.json()}


def test_workspace_source_refresh_replaces_resources_from_postgres_schema(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    def load_schema(database_url: str, *, schema_names: tuple[str, ...]) -> DatabaseSchema:
        assert database_url == "postgresql+psycopg://demo"
        assert schema_names == ("billing",)
        return _billing_schema()

    monkeypatch.setattr("databoom.api.routes.load_postgres_schema", load_schema)

    response = client.post(
        "/workspace-sources/commerce-store/refresh",
        headers=_auth_headers(token),
        json={
            "database_url": "postgresql+psycopg://demo",
            "schema_names": ["billing"],
            "default_estimated_rows": 7,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [resource["name"] for resource in payload["resources"]] == [
        "invoices",
        "invoice_lines",
    ]
    assert payload["resources"][0]["columns"] == ["id", "customer_id", "amount", "status"]
    assert payload["resources"][0]["estimated_rows"] == 7
    assert payload["resources"][0]["schema_name"] == "billing"
    assert payload["resources"][0]["primary_key"] == ["id"]
    assert payload["resources"][0]["column_details"][0] == {
        "name": "id",
        "data_type": "numeric",
        "type_family": "numeric",
        "nullable": False,
        "default": None,
        "is_primary_key": True,
        "is_foreign_key": False,
    }
    assert payload["resources"][1]["foreign_keys"][0]["columns"] == ["invoice_id"]
    assert payload["resources"][1]["foreign_keys"][0]["referred_table"] == "invoices"
    assert "FOREIGN KEY" in payload["schema_ddl"]

    detail = client.get("/workspace-sources/commerce-store")
    assert detail.status_code == 200, detail.text
    assert [resource["name"] for resource in detail.json()["resources"]] == [
        "invoices",
        "invoice_lines",
    ]


def test_product_run_uses_refreshed_workspace_source_resources(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    monkeypatch.setattr(
        "databoom.api.routes.load_postgres_schema",
        lambda database_url, *, schema_names: _billing_schema(),
    )
    refresh = client.post(
        "/workspace-sources/commerce-store/refresh",
        headers=_auth_headers(token),
        json={"database_url": "postgresql+psycopg://demo", "schema_names": ["billing"]},
    )
    assert refresh.status_code == 200, refresh.text

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "table-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    response = client.post(
        "/products/table-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {"invoices": 2, "invoice_lines": 3},
            "seed": "refreshed-source",
            "output_formats": ["csv"],
            "source_id": "commerce-store",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert [table["table_name"] for table in payload["tables"]] == [
        "billing.invoices",
        "billing.invoice_lines",
    ]
    assert payload["total_rows"] == 5

    preview = client.get(
        f"/runs/{payload['run_id']}/preview",
        params={"table": "invoice_lines", "limit": 3},
    )
    assert preview.status_code == 200, preview.text
    rows = preview.json()["rows"]
    assert {row["invoice_id"] for row in rows} <= {"1", "2"}


def test_product_run_uses_cached_source_profile_for_relationship_fanout(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    monkeypatch.setattr(
        "databoom.api.routes.load_postgres_schema",
        lambda database_url, *, schema_names: _billing_schema(),
    )
    refresh = client.post(
        "/workspace-sources/commerce-store/refresh",
        headers=_auth_headers(token),
        json={"database_url": "postgresql+psycopg://demo", "schema_names": ["billing"]},
    )
    assert refresh.status_code == 200, refresh.text

    def profile_source(database_url, source, *, top_values_limit):
        return SourceProfile(
            source_id=source.id,
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            tables=(),
            relationships=(
                RelationshipProfile(
                    child_table="invoice_lines",
                    child_schema="billing",
                    child_columns=("invoice_id",),
                    parent_table="invoices",
                    parent_schema="billing",
                    parent_columns=("id",),
                    parent_key_count=5,
                    child_row_count=10,
                    distinct_parent_keys_referenced=3,
                    min_children_per_parent=0,
                    max_children_per_parent=4,
                    average_children_per_parent=2.0,
                    empty_parent_count=2,
                    child_count_frequencies=(
                        ChildCountFrequency(child_count=0, parent_frequency=2),
                        ChildCountFrequency(child_count=1, parent_frequency=2),
                        ChildCountFrequency(child_count=4, parent_frequency=1),
                    ),
                ),
            ),
        )

    monkeypatch.setattr("databoom.api.routes.profile_postgres_source", profile_source)
    profile = client.post(
        "/workspace-sources/commerce-store/profile",
        headers=_auth_headers(token),
        json={"database_url": "postgresql+psycopg://demo"},
    )
    assert profile.status_code == 200, profile.text

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "table-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    response = client.post(
        "/products/table-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {"invoices": 5, "invoice_lines": 10},
            "seed": "profiled-source",
            "output_formats": ["csv"],
            "source_id": "commerce-store",
        },
    )

    assert response.status_code == 201, response.text
    metric = response.json()["validation"]["relationship_metrics"][0]
    assert metric["child_table"] == "billing.invoice_lines"
    assert metric["parent_table"] == "billing.invoices"
    assert metric["empty_parent_count"] == 2
    assert metric["max_children_per_parent"] == 6


def test_workspace_source_profile_returns_column_statistics(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    def profile_source(database_url, source, *, top_values_limit):
        assert database_url == "postgresql+psycopg://demo"
        assert source.id == "commerce-store"
        assert top_values_limit == 3
        return SourceProfile(
            source_id=source.id,
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
            tables=(
                TableProfile(
                    name="customers",
                    schema_name="public",
                    row_count=24,
                    columns=(
                        ColumnProfile(
                            name="status",
                            data_type="text",
                            row_count=24,
                            null_count=2,
                            null_rate=0.0833,
                            distinct_count=3,
                            min_value="active",
                            max_value="blocked",
                            top_values=(TopValue(value="active", count=18),),
                        ),
                    ),
                ),
            ),
            relationships=(
                RelationshipProfile(
                    child_table="orders",
                    child_schema="public",
                    child_columns=("customer_id",),
                    parent_table="customers",
                    parent_schema="public",
                    parent_columns=("id",),
                    parent_key_count=24,
                    child_row_count=48,
                    distinct_parent_keys_referenced=20,
                    min_children_per_parent=0,
                    max_children_per_parent=5,
                    average_children_per_parent=2.0,
                    empty_parent_count=4,
                    child_count_frequencies=(
                        ChildCountFrequency(child_count=0, parent_frequency=4),
                        ChildCountFrequency(child_count=2, parent_frequency=18),
                        ChildCountFrequency(child_count=5, parent_frequency=2),
                    ),
                ),
            ),
        )

    monkeypatch.setattr("databoom.api.routes.profile_postgres_source", profile_source)

    response = client.post(
        "/workspace-sources/commerce-store/profile",
        headers=_auth_headers(token),
        json={"database_url": "postgresql+psycopg://demo", "top_values_limit": 3},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source_id"] == "commerce-store"
    assert payload["total_rows"] == 24
    assert payload["tables"][0]["columns"][0]["null_rate"] == 0.0833
    assert payload["tables"][0]["columns"][0]["top_values"] == [
        {"value": "active", "count": 18}
    ]
    assert payload["relationships"][0]["child_table"] == "orders"
    assert payload["relationships"][0]["parent_table"] == "customers"
    assert payload["relationships"][0]["empty_parent_count"] == 4
    assert payload["relationships"][0]["child_count_frequencies"] == [
        {"child_count": 0, "parent_frequency": 4},
        {"child_count": 2, "parent_frequency": 18},
        {"child_count": 5, "parent_frequency": 2},
    ]

    snapshot = client.get(
        "/workspace-sources/commerce-store/profile",
        headers=_auth_headers(token),
    )
    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json() == payload


def test_workspace_source_profile_snapshot_returns_404_when_missing(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    response = client.get(
        "/workspace-sources/commerce-store/profile",
        headers=_auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "source profile snapshot not found"


def test_workspace_connection_test_returns_probe_result(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    def test_connection(database_url: str) -> ConnectionTest:
        assert database_url == "postgresql+psycopg://demo"
        return ConnectionTest(
            ok=True,
            message="connection ok",
            checked_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

    monkeypatch.setattr("databoom.api.routes.test_postgres_connection", test_connection)

    response = client.post(
        "/workspace-sources/test-connection",
        headers=_auth_headers(token),
        json={"database_url": "postgresql+psycopg://demo"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True
    assert response.json()["message"] == "connection ok"


def _login(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        json={"email": "operator@databoom.local", "password": "databoom-local"},
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _billing_schema() -> DatabaseSchema:
    return DatabaseSchema(
        tables=(
            TableSchema(
                name="invoices",
                schema_name="billing",
                columns=(
                    _column("id", TypeFamily.NUMERIC),
                    _column("customer_id", TypeFamily.NUMERIC),
                    _column("amount", TypeFamily.NUMERIC),
                    _column("status", TypeFamily.STRING),
                ),
                primary_key=PrimaryKeyConstraint(columns=("id",)),
                unique_constraints=(UniqueConstraint(columns=("customer_id", "status")),),
            ),
            TableSchema(
                name="invoice_lines",
                schema_name="billing",
                columns=(
                    _column("id", TypeFamily.NUMERIC),
                    _column("invoice_id", TypeFamily.NUMERIC),
                    _column("sku", TypeFamily.STRING),
                    _column("amount", TypeFamily.NUMERIC),
                ),
                primary_key=PrimaryKeyConstraint(columns=("id",)),
                foreign_keys=(
                    ForeignKeyConstraint(
                        columns=("invoice_id",),
                        referred_schema="billing",
                        referred_table="invoices",
                        referred_columns=("id",),
                        name="invoice_lines_invoice_id_fkey",
                    ),
                ),
            ),
        )
    )


def _column(name: str, family: TypeFamily) -> ColumnSchema:
    return ColumnSchema(
        name=name,
        nullable=False,
        data_type=PostgresType(
            raw="numeric" if family == TypeFamily.NUMERIC else "text",
            name="NUMERIC" if family == TypeFamily.NUMERIC else "TEXT",
            family=family,
        ),
    )
