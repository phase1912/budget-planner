"""Tests for the request-scoped session dependency (F0.3.1).

`get_engine`/`get_session_factory` are checked by asserting the arguments they
pass to SQLAlchemy, not by opening a real connection — pool sizing and the
commit/rollback boundary are generic SQLAlchemy behaviour, not something that
needs a live PostgreSQL to exercise. Alembic and the model conventions (F0.3.2,
F0.3.3, F0.3.4) are what actually needs a database, and are covered separately
in tests/db/, skipped when one isn't reachable.
"""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.session import get_db_session, get_engine, get_session_factory


@pytest.fixture(autouse=True)
def _clear_caches() -> Iterator[None]:
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    yield
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.fixture
def _settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """A fully-populated Settings, wired in so get_engine never reads real
    environment/.env — CI has neither set, and get_settings() would otherwise
    fail validation there even though it happens to succeed on a machine with
    a local .env file.
    """
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        database_pool_size=7,
        database_max_overflow=3,
        anthropic_api_key="sk-test-key",
    )
    monkeypatch.setattr("app.session.get_settings", lambda: settings)
    return settings


def test_engine_is_built_with_pool_settings_from_config(_settings: Settings) -> None:
    with patch("app.session.create_async_engine") as create_async_engine:
        get_engine()

    args, kwargs = create_async_engine.call_args
    assert args[0] == str(_settings.database_url)
    assert kwargs["pool_size"] == 7
    assert kwargs["max_overflow"] == 3
    assert kwargs["pool_pre_ping"] is True


def test_get_engine_builds_the_engine_only_once(_settings: Settings) -> None:
    with patch("app.session.create_async_engine") as create_async_engine:
        first = get_engine()
        second = get_engine()

    create_async_engine.assert_called_once()
    assert first is second


class _FakeSessionContext:
    """Async context manager standing in for `async_sessionmaker()()`."""

    def __init__(self, session: AsyncMock) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncMock:
        return self._session

    async def __aexit__(self, *exc_info: object) -> None:
        return None


async def test_session_commits_when_the_route_completes_without_error() -> None:
    session = AsyncMock(spec=AsyncSession)
    factory = MagicMock(return_value=_FakeSessionContext(session))

    async for yielded in get_db_session(session_factory=factory):
        assert yielded is session

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


async def test_session_rolls_back_and_reraises_when_the_route_raises() -> None:
    """FastAPI feeds a route's exception back into a yield-dependency via `athrow`
    (through the AsyncExitStack it wraps yield-dependencies in), not by raising
    inside a plain `async for` — so the test drives the generator the same way.
    """
    session = AsyncMock(spec=AsyncSession)
    factory = MagicMock(return_value=_FakeSessionContext(session))

    generator = get_db_session(session_factory=factory)
    yielded = await anext(generator)
    assert yielded is session

    with pytest.raises(ValueError, match="boom"):
        await generator.athrow(ValueError("boom"))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
