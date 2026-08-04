from pathlib import Path

from fastapi.testclient import TestClient

from databoom.api import create_app
from databoom.api.state import SQLAlchemyStateStore
from databoom.core.config import Settings


def test_product_flow_subscribe_generate_preview_and_download(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    products = client.get("/products")
    assert products.status_code == 200
    product_payload = products.json()
    assert {product["id"] for product in product_payload} == {
        "table-boom",
        "docu-boom",
        "graph-boom",
        "masker-boom",
    }
    assert {product["id"]: product["kind"] for product in product_payload} == {
        "table-boom": "relational",
        "docu-boom": "document",
        "graph-boom": "graph",
        "masker-boom": "masking",
    }

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "table-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text
    assert subscription.json()["status"] == "active"

    run = client.post(
        "/products/table-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {
                "customers": 2,
                "products": 2,
                "orders": 3,
                "order_items": 4,
                "payments": 3,
            },
            "seed": "product-flow",
            "output_formats": ["csv", "json"],
        },
    )
    assert run.status_code == 201, run.text
    run_payload = run.json()
    assert run_payload["kind"] == "relational"
    assert run_payload["status"] == "completed"
    assert run_payload["total_rows"] == 14
    assert run_payload["validation"]["passed"] is True

    preview = client.get(
        f"/runs/{run_payload['run_id']}/preview",
        params={"table": "payments", "limit": 3},
    )
    assert preview.status_code == 200, preview.text
    preview_payload = preview.json()
    assert preview_payload["table_name"] == "public.payments"
    assert len(preview_payload["rows"]) == 3
    assert "payment_amount" in preview_payload["columns"]

    artifacts = client.get(f"/runs/{run_payload['run_id']}/artifacts")
    assert artifacts.status_code == 200
    assert "public__payments.csv" in {
        artifact["relative_path"] for artifact in artifacts.json()["files"]
    }


def test_document_product_flow_generates_json_and_preview(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "docu-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    run = client.post(
        "/products/docu-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {"customers": 2, "orders": 3, "events": 4},
            "seed": "document-flow",
            "output_formats": ["json", "ndjson"],
        },
    )

    assert run.status_code == 201, run.text
    run_payload = run.json()
    assert run_payload["kind"] == "document"
    assert run_payload["total_rows"] == 9
    assert {collection["collection_name"] for collection in run_payload["collections"]} == {
        "customers",
        "orders",
        "events",
    }

    preview = client.get(
        f"/runs/{run_payload['run_id']}/document-preview",
        params={"collection": "customers", "limit": 2},
    )
    assert preview.status_code == 200, preview.text
    preview_payload = preview.json()
    assert preview_payload["collection_name"] == "customers"
    assert len(preview_payload["documents"]) == 2
    assert "_id" in preview_payload["documents"][0]
    assert "profile" in preview_payload["documents"][0]

    artifacts = client.get(f"/runs/{run_payload['run_id']}/artifacts")
    assert artifacts.status_code == 200
    assert "customers.ndjson" in {
        artifact["relative_path"] for artifact in artifacts.json()["files"]
    }


def test_product_run_requires_subscription(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    response = client.post(
        "/products/docu-boom/runs",
        headers=_auth_headers(token),
        json={"seed": "no-subscription"},
    )

    assert response.status_code == 403


def test_planned_product_cannot_generate(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "graph-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    response = client.post(
        "/products/graph-boom/runs",
        headers=_auth_headers(token),
        json={"seed": "planned-product"},
    )

    assert response.status_code == 400
    assert "not runnable yet" in response.json()["detail"]


def test_demo_login_rejects_invalid_password(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))

    response = client.post("/auth/login", json={"email": "demo", "password": "wrong"})

    assert response.status_code == 401


def test_sql_state_store_persists_demo_flow_across_app_instances(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'state.db'}"
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")

    first_client = TestClient(
        create_app(settings=settings, state_store=SQLAlchemyStateStore(database_url))
    )
    token = _login(first_client)
    subscription = first_client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "table-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    run = first_client.post(
        "/products/table-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {
                "customers": 1,
                "products": 1,
                "orders": 2,
                "order_items": 2,
                "payments": 2,
            },
            "seed": "persisted-flow",
            "output_formats": ["csv", "json"],
        },
    )
    assert run.status_code == 201, run.text
    run_id = run.json()["run_id"]

    second_client = TestClient(
        create_app(settings=settings, state_store=SQLAlchemyStateStore(database_url))
    )

    me = second_client.get("/me", headers=_auth_headers(token))
    subscriptions = second_client.get("/subscriptions", headers=_auth_headers(token))
    stored_run = second_client.get(f"/runs/{run_id}")
    preview = second_client.get(
        f"/runs/{run_id}/preview",
        params={"table": "payments", "limit": 2},
    )

    assert me.status_code == 200
    assert subscriptions.status_code == 200
    assert subscriptions.json()[0]["product_id"] == "table-boom"
    assert stored_run.status_code == 200
    assert stored_run.json()["run_id"] == run_id
    assert preview.status_code == 200
    assert len(preview.json()["rows"]) == 2


def _login(client: TestClient) -> str:
    response = client.post("/auth/login", json={"email": "demo", "password": "demo"})
    assert response.status_code == 200
    return str(response.json()["token"])


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
