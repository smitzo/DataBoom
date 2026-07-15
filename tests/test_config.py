from pathlib import Path

from boom_data.core.config import Settings


def test_settings_normalize_log_level() -> None:
    settings = Settings(LOG_LEVEL="debug")

    assert settings.log_level == "DEBUG"


def test_artifact_root_resolves_to_absolute_path(tmp_path: Path) -> None:
    settings = Settings(ARTIFACT_ROOT=tmp_path / "runs")

    assert settings.resolve_artifact_root() == (tmp_path / "runs").resolve()
