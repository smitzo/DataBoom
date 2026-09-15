from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

from databoom.api import create_app
from databoom.api.state import SQLAlchemyStateStore
from databoom.core.config import Settings


def test_plan_review_and_approved_execution_flow(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    with TestClient(create_app(settings=settings)) as client:
        token = _register(client, "planner@example.test")
        _subscribe(client, token, "graph-boom")

        plan_response = client.post(
            "/products/graph-boom/plans",
            headers=_headers(token),
            json={
                "intent": "Create a compact fraud-network graph for integration tests.",
                "row_counts": {
                    "Customer": 2,
                    "Account": 2,
                    "Device": 1,
                    "OWNS": 2,
                    "USES_DEVICE": 2,
                    "TRANSFERRED_TO": 2,
                },
                "seed": "reviewed-graph-plan",
                "output_formats": ["json", "csv"],
            },
        )

        assert plan_response.status_code == 201, plan_response.text
        plan = plan_response.json()
        assert plan["review_status"] == "draft"
        assert plan["telemetry"]["mode"] == "deterministic"
        assert sum(item["target_count"] for item in plan["decision"]["resources"]) == 11

        blocked = client.post(
            f"/plans/{plan['plan_id']}/runs/async",
            headers=_headers(token),
            json={},
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"] == "approve the plan before generation"

        review = client.post(
            f"/plans/{plan['plan_id']}/review",
            headers=_headers(token),
            json={"status": "approved"},
        )
        assert review.status_code == 200, review.text
        assert review.json()["reviewed_by"] == "planner@example.test"

        started = client.post(
            f"/plans/{plan['plan_id']}/runs/async",
            headers=_headers(token),
            json={},
        )
        assert started.status_code == 202, started.text
        assert started.json()["plan_id"] == plan["plan_id"]

        completed = _wait_for_run(client, started.json()["run_id"])
        assert completed["status"] == "completed"
        assert completed["plan_id"] == plan["plan_id"]
        assert completed["validation"]["passed"] is True


def test_plans_are_private_and_validate_resource_names(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    with TestClient(create_app(settings=settings)) as client:
        owner_token = _register(client, "owner@example.test")
        other_token = _register(client, "other@example.test")
        _subscribe(client, owner_token, "table-boom")

        invalid = client.post(
            "/products/table-boom/plans",
            headers=_headers(owner_token),
            json={
                "intent": "Generate test data.",
                "row_counts": {"not_a_table": 5},
            },
        )
        assert invalid.status_code == 400
        assert "unknown planning resources" in invalid.json()["detail"]

        created = client.post(
            "/products/table-boom/plans",
            headers=_headers(owner_token),
            json={"intent": "Generate the default relational integration dataset."},
        )
        assert created.status_code == 201, created.text
        plan_id = created.json()["plan_id"]

        assert client.get(f"/plans/{plan_id}", headers=_headers(other_token)).status_code == 404
        plans = client.get("/plans", headers=_headers(owner_token))
        assert plans.status_code == 200
        assert [plan["plan_id"] for plan in plans.json()] == [plan_id]


def test_plan_infers_locale_and_preserves_it_during_execution(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    with TestClient(create_app(settings=settings)) as client:
        token = _register(client, "locale-planner@example.test")
        _subscribe(client, token, "table-boom")
        created = client.post(
            "/products/table-boom/plans",
            headers=_headers(token),
            json={
                "intent": "Generate Indian customers located in Mumbai and Bengaluru.",
                "row_counts": {
                    "customers": 4,
                    "products": 2,
                    "orders": 4,
                    "order_items": 4,
                    "payments": 4,
                },
            },
        )

        assert created.status_code == 201, created.text
        assert created.json()["locale"] == "en-IN"
        reviewed = client.post(
            f"/plans/{created.json()['plan_id']}/review",
            headers=_headers(token),
            json={"status": "approved"},
        )
        started = client.post(
            f"/plans/{reviewed.json()['plan_id']}/runs/async",
            headers=_headers(token),
            json={},
        )
        completed = _wait_for_run(client, started.json()["run_id"])

        assert completed["locale"] == "en-IN"
        preview = client.get(
            f"/runs/{completed['run_id']}/preview",
            params={"table": "customers", "limit": 4},
        )
        assert preview.status_code == 200, preview.text
        assert all(row["phone"].startswith("+91") for row in preview.json()["rows"])
        assert all(
            row["full_name"] != f"Full Name {index}"
            for index, row in enumerate(preview.json()["rows"], 1)
        )


def test_sql_state_store_persists_reviewed_plan(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'plans.db'}"
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    with TestClient(
        create_app(settings=settings, state_store=SQLAlchemyStateStore(database_url))
    ) as first_client:
        token = _register(first_client, "persisted-planner@example.test")
        _subscribe(first_client, token, "docu-boom")
        created = first_client.post(
            "/products/docu-boom/plans",
            headers=_headers(token),
            json={"intent": "Create nested documents for API contract tests."},
        )
        plan_id = created.json()["plan_id"]
        reviewed = first_client.post(
            f"/plans/{plan_id}/review",
            headers=_headers(token),
            json={"status": "approved"},
        )
        assert reviewed.status_code == 200, reviewed.text

    with TestClient(
        create_app(settings=settings, state_store=SQLAlchemyStateStore(database_url))
    ) as second_client:
        stored = second_client.get(f"/plans/{plan_id}", headers=_headers(token))

    assert stored.status_code == 200, stored.text
    assert stored.json()["review_status"] == "approved"
    assert stored.json()["reviewed_by"] == "persisted-planner@example.test"


def _register(client: TestClient, email: str) -> str:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "planner-password"},
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def _subscribe(client: TestClient, token: str, product_id: str) -> None:
    response = client.post(
        "/subscriptions",
        headers=_headers(token),
        json={"product_id": product_id, "plan_id": "starter"},
    )
    assert response.status_code == 201, response.text


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _wait_for_run(client: TestClient, run_id: str) -> dict[str, object]:
    for _attempt in range(100):
        response = client.get(f"/runs/{run_id}")
        assert response.status_code == 200, response.text
        payload = response.json()
        if payload["status"] != "running":
            return payload
        sleep(0.01)
    raise AssertionError("planned run did not complete")
