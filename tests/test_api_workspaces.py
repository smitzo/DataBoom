from pathlib import Path

from fastapi.testclient import TestClient

from databoom.api import create_app
from databoom.core.config import Settings
from databoom.schema import (
    ColumnSchema,
    DatabaseSchema,
    PostgresType,
    PrimaryKeyConstraint,
    TableSchema,
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
        "public.invoices",
        "public.invoice_lines",
    ]
    assert payload["total_rows"] == 5


def _login(client: TestClient) -> str:
    response = client.post("/auth/login", json={"email": "demo", "password": "demo"})
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
