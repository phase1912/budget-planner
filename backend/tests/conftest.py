"""Shared pytest fixtures: async support and an isolated test database (F0.6.1).

Every fixture here is opt-in — requesting `db_session` (directly, or through a
factory) is what pulls in the test database; a unit test that never asks for it
never touches PostgreSQL, which is what keeps the fast unit suite fast
(CLAUDE.md's "unit tests for business rules run without a database").

See `test_database_url` and `db_session` below for how isolation actually works.
"""

import asyncio
import os
from collections.abc import AsyncIterator, Coroutine, Iterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["S3_ENDPOINT_URL"] = "http://localhost:9000"
import pytest_asyncio
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.core.config import get_settings
from tests.factories.base import ModelFactory

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def pytest_bdd_apply_tag(tag: str, function: object) -> bool:
    """Treat every Gherkin tag as plain metadata for F0.6.4, not a pytest mark.

    Without this, pytest-bdd's default hook would turn each of the ~55 BRD
    requirement-ID tags into an unregistered `pytest.mark`. Returning a truthy
    value short-circuits that (the hook is `firstresult=True`).
    """
    return True


def _run[T](coro: Coroutine[object, object, T]) -> T:
    return asyncio.run(coro)


def _test_database_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    return urlunsplit(parts._replace(path=f"{parts.path}_test"))


def _database_name(database_url: str) -> str:
    return urlsplit(database_url).path.lstrip("/")


async def _server_is_reachable(database_url: str) -> bool:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return False
    finally:
        await engine.dispose()
    return True


async def _recreate_test_database(admin_database_url: str, test_database_url: str) -> None:
    """Drop and recreate the test database, connected to a sibling database.

    PostgreSQL cannot drop the database a connection is currently using, so this
    connects to `admin_database_url` (the ordinary dev/CI database) to manage the
    `..._test` one next to it. Runs outside a transaction block (`AUTOCOMMIT`)
    because `CREATE`/`DROP DATABASE` are not transactional statements.
    """
    test_db_name = _database_name(test_database_url)
    admin_engine = create_async_engine(
        admin_database_url, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    try:
        async with admin_engine.connect() as connection:
            await connection.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}" WITH (FORCE)'))
            await connection.execute(text(f'CREATE DATABASE "{test_db_name}"'))
    finally:
        await admin_engine.dispose()


def _migrate_to_head(database_url: str) -> None:
    """Run the real Alembic migrations against `database_url`.

    `alembic/env.py` deliberately sources its URL from `app.config.Settings`
    rather than any value passed to `Config` (F0.3.2's single-source-of-truth for
    DATABASE_URL), so the only way to point a migration run at another database is
    to make Settings resolve to it: swap the environment variable it reads, clear
    the `lru_cache`s that would otherwise serve the previous URL, run, then put
    both back exactly as found.
    """
    original_env = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    try:
        command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    finally:
        if original_env is None:
            del os.environ["DATABASE_URL"]
        else:
            os.environ["DATABASE_URL"] = original_env
        get_settings.cache_clear()


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    """The isolated database this test session runs against, migrated to `head`.

    Skips every test that depends on it (directly or via `db_session`) when no
    PostgreSQL is reachable — `docker compose up -d postgres` (F0.4.1) provides
    one for local development, and backend-ci.yml's service container (F0.5.1)
    provides one in CI.
    """
    try:
        admin_url = str(get_settings().database_url)
    except Exception:
        pytest.skip("DATABASE_URL is not configured — copy backend/.env.example to .env.")

    if not _run(_server_is_reachable(admin_url)):
        pytest.skip(
            "PostgreSQL is not reachable at DATABASE_URL — "
            "start it with `docker compose up -d postgres`."
        )

    test_url = _test_database_url(admin_url)
    _run(_recreate_test_database(admin_url, test_url))
    _migrate_to_head(test_url)
    yield test_url


@pytest_asyncio.fixture
async def db_session(test_database_url: str) -> AsyncIterator[AsyncSession]:
    """A per-test `AsyncSession` whose writes never outlive the test.

    Joins the session to the connection's own transaction with
    `join_transaction_mode="create_savepoint"`, so test code calling
    `session.commit()` only releases a SAVEPOINT — the outer rollback at
    teardown still discards everything. Also binds
    `ModelFactory.__async_session__` for the test's duration.
    """
    engine: AsyncEngine = create_async_engine(test_database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(
                bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
            )
            ModelFactory.__async_session__ = session
            try:
                yield session
            finally:
                ModelFactory.__async_session__ = None
                await session.close()
                await transaction.rollback()
    finally:
        await engine.dispose()
