"""Tests for the typed settings module (F0.2.2).

Covers what this task delivers: env-var layering (an explicit environment
variable beats the same key in a `.env` file) and fail-fast validation —
constructing `Settings` without a required variable raises immediately
instead of deferring the failure to wherever the value is first used.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings

REQUIRED_ENV = {
    "DATABASE_URL": "postgresql://user:pass@localhost:5432/budget_planner",
    "ANTHROPIC_API_KEY": "sk-test-key",
}


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)


def test_settings_loads_required_fields_from_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_env(monkeypatch)

    settings = Settings(_env_file=None)

    assert "localhost" in str(settings.database_url)
    assert settings.anthropic_api_key.get_secret_value() == "sk-test-key"
    assert settings.environment == "development"


def test_settings_raises_when_a_required_variable_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_dotenv_file_is_read_when_a_value_is_not_set_in_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "DATABASE_URL=postgresql://dotenv-user:pass@dotenv-host:5432/db\n"
        "ANTHROPIC_API_KEY=dotenv-key\n"
    )

    settings = Settings(_env_file=dotenv_path)

    assert "dotenv-host" in str(settings.database_url)
    assert settings.anthropic_api_key.get_secret_value() == "dotenv-key"


def test_environment_variable_overrides_the_dotenv_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "DATABASE_URL=postgresql://dotenv-user:pass@dotenv-host:5432/db\n"
        "ANTHROPIC_API_KEY=dotenv-key\n"
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql://envvar-user:pass@envvar-host:5432/db")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "envvar-key")

    settings = Settings(_env_file=dotenv_path)

    assert "envvar-host" in str(settings.database_url)
    assert settings.anthropic_api_key.get_secret_value() == "envvar-key"


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    get_settings.cache_clear()

    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()


def test_no_direct_os_environ_reads_outside_the_config_module() -> None:
    """A raw os.environ/os.getenv read bypasses Settings' fail-fast validation."""
    app_root = Path(__file__).resolve().parent.parent / "app"
    config_module = app_root / "config.py"

    offending = [
        str(path.relative_to(app_root))
        for path in app_root.rglob("*.py")
        if path != config_module
        and ("os.environ" in path.read_text() or "os.getenv" in path.read_text())
    ]

    assert offending == []
