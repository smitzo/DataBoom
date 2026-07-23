from pathlib import Path

from fastapi.testclient import TestClient

from boom_data.api import create_app
from boom_data.core.config import Settings


def test_create_generation_run_writes_artifacts(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))

    response = _create_generation_run(client)

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["total_rows"] == 5
    assert payload["table_count"] == 2
    assert payload["validation"]["passed"] is True
    assert Path(payload["manifest_path"]).exists()
    assert Path(payload["validation_path"]).exists()

    stored = client.get(f"/runs/{payload['run_id']}")
    assert stored.status_code == 200
    assert stored.json()["run_id"] == payload["run_id"]


def test_list_generation_run_artifacts(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    run = _create_generation_run(client).json()

    response = client.get(f"/runs/{run['run_id']}/artifacts")

    assert response.status_code == 200
    payload = response.json()
    artifact_names = {artifact["relative_path"] for artifact in payload["files"]}
    assert payload["run_id"] == run["run_id"]
    assert {
        "manifest.json",
        "validation.json",
        "public__accounts.csv",
        "public__users.csv",
        "public__users.json",
        "public__users.sql",
    } <= artifact_names
    assert all(artifact["size_bytes"] > 0 for artifact in payload["files"])


def test_download_generation_run_artifact(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    run = _create_generation_run(client).json()

    response = client.get(f"/runs/{run['run_id']}/artifacts/public__users.csv")

    assert response.status_code == 200
    assert response.text.splitlines()[0] == "id,account_id,email"


def test_download_generation_run_artifact_rejects_path_traversal(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))
    run = _create_generation_run(client).json()
    (tmp_path / "artifacts" / "secret.txt").write_text("not a run artifact", encoding="utf-8")

    response = client.get(f"/runs/{run['run_id']}/artifacts/%2E%2E/secret.txt")

    assert response.status_code == 400


def test_list_generation_runs_returns_current_process_runs(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))

    response = client.get("/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_create_generation_run_rejects_invalid_schema(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "artifacts")
    client = TestClient(create_app(settings=settings))

    response = client.post(
        "/runs",
        json={
            "schema_ddl": "CREATE VIEW users AS SELECT 1;",
            "row_counts": {},
            "output_formats": ["csv"],
        },
    )

    assert response.status_code == 400


def _create_generation_run(client: TestClient):
    return client.post(
        "/runs",
        json={
            "schema_ddl": """
                CREATE TABLE accounts (id bigint PRIMARY KEY, name text NOT NULL);
                CREATE TABLE users (
                    id bigint PRIMARY KEY,
                    account_id bigint NOT NULL REFERENCES accounts(id),
                    email text NOT NULL
                );
            """,
            "row_counts": {"accounts": 2, "users": 3},
            "seed": "api-demo",
            "domain": "general",
            "output_formats": ["csv", "json", "sql"],
        },
    )
