from datetime import UTC, datetime
from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

from databoom.api import create_app
from databoom.api.models import (
    GenerationRunResponse,
    OperationStatus,
    OperationTimingResponse,
    RunStatus,
)
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
    assert run_payload["generated_rows"] == 14
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
            "locale": "en-IN",
            "output_formats": ["json", "ndjson"],
        },
    )

    assert run.status_code == 201, run.text
    run_payload = run.json()
    assert run_payload["kind"] == "document"
    assert run_payload["total_rows"] == 9
    assert run_payload["generated_rows"] == 9
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
    customer = preview_payload["documents"][0]
    assert customer["phone"].startswith("+91")
    assert customer["addresses"][0]["country"] == "IN"
    assert len(customer["addresses"][0]["postal_code"]) == 6
    assert customer["profile"]["gender"] in {"female", "male"}
    assert customer["profile"]["first_name"].casefold() in customer["email"]

    artifacts = client.get(f"/runs/{run_payload['run_id']}/artifacts")
    assert artifacts.status_code == 200
    assert "customers.ndjson" in {
        artifact["relative_path"] for artifact in artifacts.json()["files"]
    }


def test_graph_product_flow_generates_nodes_edges_and_preview(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "graph-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    run = client.post(
        "/products/graph-boom/runs",
        headers=_auth_headers(token),
        json={
            "row_counts": {
                "Customer": 2,
                "Account": 2,
                "Device": 1,
                "OWNS": 2,
                "USES_DEVICE": 2,
                "TRANSFERRED_TO": 2,
            },
            "seed": "graph-flow",
            "output_formats": ["json", "csv"],
        },
    )

    assert run.status_code == 201, run.text
    run_payload = run.json()
    assert run_payload["kind"] == "graph"
    assert run_payload["total_rows"] == 11
    assert run_payload["generated_rows"] == 11
    assert run_payload["graph"]["node_count"] == 5
    assert run_payload["graph"]["edge_count"] == 6
    assert run_payload["validation"]["passed"] is True
    assert set(run_payload["validation"]["checked_tables"]) == {"nodes", "edges"}

    preview = client.get(
        f"/runs/{run_payload['run_id']}/graph-preview",
        params={"node_limit": 2, "edge_limit": 2},
    )
    assert preview.status_code == 200, preview.text
    preview_payload = preview.json()
    assert len(preview_payload["nodes"]) == 2
    assert len(preview_payload["edges"]) == 2
    assert preview_payload["nodes"][0]["label"] == "Customer"
    assert {"source", "target"} <= set(preview_payload["edges"][0])

    artifacts = client.get(f"/runs/{run_payload['run_id']}/artifacts")
    assert artifacts.status_code == 200
    assert {"graph.json", "nodes.csv", "edges.csv"} <= {
        artifact["relative_path"] for artifact in artifacts.json()["files"]
    }


def test_document_preview_falls_back_to_ndjson_when_json_is_incomplete(
    tmp_path: Path,
) -> None:
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
            "row_counts": {"customers": 3, "orders": 3, "events": 3},
            "seed": "document-fallback",
            "output_formats": ["json", "ndjson"],
        },
    )
    assert run.status_code == 201, run.text

    customers = next(
        collection
        for collection in run.json()["collections"]
        if collection["collection_name"] == "customers"
    )
    Path(customers["json_path"]).write_text('[\n{"_id":', encoding="utf-8")

    preview = client.get(
        f"/runs/{run.json()['run_id']}/document-preview",
        params={"collection": "customers", "limit": 2},
    )

    assert preview.status_code == 200, preview.text
    assert len(preview.json()["documents"]) == 2
    assert "_id" in preview.json()["documents"][0]


def test_async_product_run_reports_progress_and_timings(tmp_path: Path) -> None:
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
        "/products/table-boom/runs/async",
        headers=_auth_headers(token),
        json={
            "row_counts": {
                "customers": 2,
                "products": 2,
                "orders": 3,
                "order_items": 4,
                "payments": 3,
            },
            "seed": "async-product-flow",
            "output_formats": ["csv", "json"],
        },
    )

    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["status"] == "running"
    assert payload["generated_rows"] == 0
    assert payload["current_operation"] == "export_artifacts"
    assert payload["expected_seconds"] > 0
    assert payload["operation_timings"][0]["status"] == "running"

    completed = _wait_for_run(client, payload["run_id"])
    assert completed["status"] == "completed"
    assert completed["generated_rows"] == completed["total_rows"]
    assert completed["progress_percent"] == 100
    assert completed["validation"]["passed"] is True
    assert {timing["operation"] for timing in completed["operation_timings"]} >= {
        "parse_schema",
        "build_plan",
        "export_artifacts",
        "validate_artifacts",
        "total_run",
    }

    preview = client.get(
        f"/runs/{payload['run_id']}/preview",
        params={"table": "payments", "limit": 2},
    )
    assert preview.status_code == 200
    assert len(preview.json()["rows"]) == 2

    retry_completed = client.post(f"/runs/{payload['run_id']}/retry")
    assert retry_completed.status_code == 409


def test_async_product_run_can_cancel_running_run(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "table-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    def slow_execute(
        product,
        payload,
        settings,
        *,
        run_id=None,
        created_at=None,
        artifact_dir=None,
        progress_callback=None,
    ):
        created_at = created_at or datetime.now(UTC)
        for generated_rows in range(1, 50):
            if progress_callback is not None:
                progress_callback(generated_rows, "customers")
            sleep(0.01)
        return _fake_completed_product_run(
            product,
            payload,
            run_id=run_id,
            created_at=created_at,
            artifact_dir=artifact_dir or tmp_path,
            total_rows=50,
        )

    monkeypatch.setattr(
        "databoom.api.async_jobs.execute_product_generation_run",
        slow_execute,
    )

    response = client.post(
        "/products/table-boom/runs/async",
        headers=_auth_headers(token),
        json={"row_counts": {"customers": 50}, "seed": "cancel-flow", "output_formats": ["csv"]},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["run_id"]

    canceled = client.post(f"/runs/{run_id}/cancel")
    assert canceled.status_code == 200, canceled.text
    canceled_payload = canceled.json()
    assert canceled_payload["status"] == "canceled"
    assert canceled_payload["error"] == "run canceled by user"
    assert canceled_payload["operation_timings"][0]["status"] == "canceled"

    stored = client.get(f"/runs/{run_id}")
    assert stored.status_code == 200
    assert stored.json()["status"] == "canceled"


def test_async_product_run_retries_failed_run(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    subscription = client.post(
        "/subscriptions",
        headers=_auth_headers(token),
        json={"product_id": "table-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    calls = 0

    def flaky_execute(
        product,
        payload,
        settings,
        *,
        run_id=None,
        created_at=None,
        artifact_dir=None,
        progress_callback=None,
    ):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("forced generation failure")
        created_at = created_at or datetime.now(UTC)
        if progress_callback is not None:
            progress_callback(3, "customers")
        return _fake_completed_product_run(
            product,
            payload,
            run_id=run_id,
            created_at=created_at,
            artifact_dir=artifact_dir or tmp_path,
            total_rows=3,
        )

    monkeypatch.setattr(
        "databoom.api.async_jobs.execute_product_generation_run",
        flaky_execute,
    )

    response = client.post(
        "/products/table-boom/runs/async",
        headers=_auth_headers(token),
        json={"row_counts": {"customers": 3}, "seed": "retry-flow", "output_formats": ["csv"]},
    )
    assert response.status_code == 202, response.text

    failed = _wait_for_run(client, response.json()["run_id"])
    assert failed["status"] == "failed"
    assert failed["error"] == "RuntimeError: forced generation failure"

    retry = client.post(f"/runs/{failed['run_id']}/retry")
    assert retry.status_code == 202, retry.text
    retry_payload = retry.json()
    assert retry_payload["status"] == "running"
    assert retry_payload["retry_of_run_id"] == failed["run_id"]

    completed = _wait_for_run(client, retry_payload["run_id"])
    assert completed["status"] == "completed"
    assert completed["retry_of_run_id"] == failed["run_id"]
    assert completed["generated_rows"] == 3


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
        json={"product_id": "masker-boom", "plan_id": "starter"},
    )
    assert subscription.status_code == 201, subscription.text

    response = client.post(
        "/products/masker-boom/runs",
        headers=_auth_headers(token),
        json={"seed": "planned-product"},
    )

    assert response.status_code == 400
    assert "not runnable yet" in response.json()["detail"]


def test_login_rejects_invalid_password(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))

    response = client.post(
        "/auth/login",
        json={"email": "operator@databoom.local", "password": "wrong"},
    )

    assert response.status_code == 401


def test_registration_rejects_duplicate_email(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))

    response = client.post(
        "/auth/register",
        json={
            "email": "team-alpha@databoom.local",
            "password": "strong-password",
        },
    )
    duplicate = client.post(
        "/auth/register",
        json={
            "email": "team-alpha@databoom.local",
            "password": "strong-password",
        },
    )

    assert response.status_code == 201, response.text
    assert duplicate.status_code == 409


def test_llm_policy_prefers_user_key_over_platform_key(tmp_path: Path) -> None:
    settings = Settings(
        ENV="test",
        ARTIFACT_ROOT=tmp_path / "artifacts",
        DATABOOM_LLM_PLATFORM_API_KEY="platform-key",
    )
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    platform_policy = client.get("/llm/policy", headers=_auth_headers(token))
    user_policy = client.post(
        "/llm/policy",
        headers=_auth_headers(token),
        json={"user_api_key": "user-key"},
    )

    assert platform_policy.status_code == 200, platform_policy.text
    assert platform_policy.json()["active_mode"] == "platform_key"
    assert platform_policy.json()["platform_key_configured"] is True
    assert platform_policy.json()["llm_enabled"] is True
    assert user_policy.status_code == 200, user_policy.text
    assert user_policy.json()["active_mode"] == "user_key"
    assert user_policy.json()["user_key_supplied"] is True
    assert "user-key" not in user_policy.text


def test_llm_policy_falls_back_without_keys(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    token = _login(client)

    response = client.get("/llm/policy", headers=_auth_headers(token))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["active_mode"] == "deterministic_fallback"
    assert payload["llm_enabled"] is False
    assert payload["deterministic_fallback_available"] is True


def test_sql_state_store_persists_app_flow_across_app_instances(tmp_path: Path) -> None:
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
    response = client.post(
        "/auth/login",
        json={"email": "operator@databoom.local", "password": "databoom-local"},
    )
    assert response.status_code == 200
    return str(response.json()["token"])


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _fake_completed_product_run(
    product,
    payload,
    *,
    run_id: str | None,
    created_at: datetime,
    artifact_dir: Path,
    total_rows: int,
) -> GenerationRunResponse:
    completed_at = datetime.now(UTC)
    return GenerationRunResponse(
        run_id=run_id or "fake-run",
        kind=product.kind,
        status=RunStatus.COMPLETED,
        created_at=created_at,
        completed_at=completed_at,
        artifact_dir=artifact_dir,
        domain=product.domain,
        output_formats=tuple(payload.output_formats or product.output_formats),
        total_rows=total_rows,
        table_count=1,
        generated_rows=total_rows,
        progress_percent=100.0,
        current_operation="complete",
        operation_timings=(
            OperationTimingResponse(
                operation="generate_async",
                status=OperationStatus.COMPLETED,
                elapsed_seconds=round((completed_at - created_at).total_seconds(), 3),
                started_at=created_at,
                completed_at=completed_at,
            ),
        ),
    )


def _wait_for_run(client: TestClient, run_id: str) -> dict:
    for _ in range(50):
        response = client.get(f"/runs/{run_id}")
        assert response.status_code == 200, response.text
        payload = response.json()
        if payload["status"] != "running":
            return payload
        sleep(0.05)
    raise AssertionError("async run did not finish")
