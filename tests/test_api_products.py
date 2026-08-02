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
    assert {"bank-o-boom", "health-boom", "boom-commerce", "schema-boom"} <= {
        product["id"] for product in products.json()
    }

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "bank-o-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text
    assert subscription.json()["status"] == "active"

    run = client.post(
        "/products/bank-o-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {"customers": 2, "bank_accounts": 3, "transactions": 4},
            "seed": "product-flow",
            "output_formats": ["csv", "json"],
        },
    )
    assert run.status_code == 201, run.text
    run_payload = run.json()
    assert run_payload["status"] == "completed"
    assert run_payload["total_rows"] == 9
    assert run_payload["validation"]["passed"] is True

    preview = client.get(
        f"/runs/{run_payload['run_id']}/preview",
        params={"table": "transactions", "limit": 3},
    )
    assert preview.status_code == 200, preview.text
    preview_payload = preview.json()
    assert preview_payload["table_name"] == "public.transactions"
    assert len(preview_payload["rows"]) == 3
    assert "amount" in preview_payload["columns"]

    artifacts = client.get(f"/runs/{run_payload['run_id']}/artifacts")
    assert artifacts.status_code == 200
    assert "public__transactions.csv" in {
        artifact["relative_path"] for artifact in artifacts.json()["files"]
    }


def test_product_run_requires_subscription(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    response = client.post(
        "/products/health-boom/runs",
        headers=_auth_headers(token),
        json={"seed": "no-subscription"},
    )

    assert response.status_code == 403


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
        json={"product_id": "schema-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    run = first_client.post(
        "/products/schema-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {"organizations": 1, "users": 2, "audit_events": 3},
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
        params={"table": "audit_events", "limit": 2},
    )

    assert me.status_code == 200
    assert subscriptions.status_code == 200
    assert subscriptions.json()[0]["product_id"] == "schema-boom"
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
