from pathlib import Path

from fastapi.testclient import TestClient

from databoom.api import create_app
from databoom.core.config import Settings


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


def _login(client: TestClient) -> str:
    response = client.post("/auth/login", json={"email": "demo", "password": "demo"})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
