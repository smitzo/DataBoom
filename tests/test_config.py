from pathlib import Path

from databoom.core.config import Settings


def test_settings_normalize_log_level() -> None:
    settings = Settings(LOG_LEVEL="debug")

    assert settings.log_level == "DEBUG"


def test_artifact_root_resolves_to_absolute_path(tmp_path: Path) -> None:
    settings = Settings(ARTIFACT_ROOT=tmp_path / "runs")

    assert settings.resolve_artifact_root() == (tmp_path / "runs").resolve()


def test_settings_include_local_service_urls() -> None:
    settings = Settings()

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.redis_url.startswith("redis://")


def test_empty_api_key_disables_api_key_authentication() -> None:
    settings = Settings(API_KEY="")

    assert settings.api_key is None


def test_settings_read_databoom_prefixed_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABOOM_ENV", "docker")
    monkeypatch.setenv("DATABOOM_ARTIFACT_ROOT", str(tmp_path / "docker-artifacts"))
    monkeypatch.setenv("DATABOOM_LOG_LEVEL", "debug")
    monkeypatch.setenv("DATABOOM_CORS_ORIGINS", "http://localhost:3001,http://127.0.0.1:3001")

    settings = Settings()

    assert settings.environment == "docker"
    assert settings.artifact_root == tmp_path / "docker-artifacts"
    assert settings.log_level == "DEBUG"
    assert settings.cors_origins == ("http://localhost:3001", "http://127.0.0.1:3001")
