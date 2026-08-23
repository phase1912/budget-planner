"""Tests for the typed settings module (F0.2.2, F0.7.1).

Covers what this task delivers: env-var layering (an explicit environment
variable beats the same key in a `.env` file) and fail-fast validation —
constructing `Settings` without a required variable raises immediately
instead of deferring the failure to wherever the value is first used. Also
covers the F0.7.1 settings added on top: the `Environment` enum and the
confidence thresholds' bounds (BRD A10, C3).
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Environment, Settings, get_settings

REQUIRED_ENV = {
    "DATABASE_URL": "postgresql://user:pass@localhost:5432/budget_planner",
    "ANTHROPIC_API_KEY": "sk-test-key",
    "JWT_SECRET_KEY": "test-secret-key-that-is-not-default",
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
    assert settings.environment is Environment.LOCAL


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


def test_environment_variable_selects_a_deployment_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.PRODUCTION


def test_an_unrecognised_environment_value_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "prod")  # not a member of Environment

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_anthropic_model_defaults_to_the_local_staging_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_env(monkeypatch)

    settings = Settings(_env_file=None)

    assert settings.anthropic_model == "claude-haiku-4-5-20251001"


def test_anthropic_model_is_overridable_per_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    settings = Settings(_env_file=None)

    assert settings.anthropic_model == "claude-sonnet-5"


def test_confidence_thresholds_default_per_brd_a10_and_c3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_env(monkeypatch)

    settings = Settings(_env_file=None)

    assert settings.ocr_confidence_threshold == 0.80
    assert settings.categorization_confidence_threshold == 0.70


@pytest.mark.parametrize("value", ["-0.1", "1.1"])
def test_confidence_thresholds_reject_values_outside_zero_to_one(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("OCR_CONFIDENCE_THRESHOLD", value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


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
