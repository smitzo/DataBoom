from pathlib import Path

from fastapi.testclient import TestClient

from boom_data import __version__
from boom_data.api import create_app
from boom_data.core.config import Settings


def test_health_endpoint_returns_runtime_context(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "runs")
    client = TestClient(create_app(settings=settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "boom-data-api",
        "version": __version__,
        "environment": "test",
        "artifact_root": str((tmp_path / "runs").resolve()),
    }


def test_ready_endpoint_matches_health_contract(tmp_path: Path) -> None:
    settings = Settings(ENV="test", ARTIFACT_ROOT=tmp_path / "runs")
    client = TestClient(create_app(settings=settings))

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "boom-data-api"
