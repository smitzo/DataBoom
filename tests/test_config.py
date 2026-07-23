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
