"""Integration tests for the F0.3 database baseline: Alembic + PostgreSQL (F0.3.2, F0.3.4).

Skipped when PostgreSQL isn't reachable at the configured DATABASE_URL —
`docker compose up -d postgres` (F0.4.1) provides one for local development.
CI does not yet run a service-container PostgreSQL of its own (that is
F0.5.1), so today this only runs for a developer with the compose stack up;
once F0.5.1 lands it starts running for real in CI with no change here.

Runs synchronously (not `async def`) because `alembic.command.upgrade` drives
its own event loop internally (see alembic/env.py's async template) — calling
it from inside a coroutine already running under pytest-asyncio would try to
nest event loops.
"""

import asyncio
from collections.abc import Coroutine
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from app.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def _run[T](coro: Coroutine[object, object, T]) -> T:
    return asyncio.run(coro)


async def _database_is_reachable() -> bool:
    """False for anything short of a live, queryable PostgreSQL.

    Includes Settings() itself failing validation — CI has neither DATABASE_URL
    nor a .env file set until F0.5.1 adds a service-container PostgreSQL, so
    that has to be "not reachable" here too, not an uncaught error.
    """
    try:
        engine = create_async_engine(str(get_settings().database_url))
    except Exception:
        return False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return False
    finally:
        await engine.dispose()
    return True


@pytest.fixture(autouse=True)
def _require_database() -> None:
    if not _run(_database_is_reachable()):
        pytest.skip(
            "PostgreSQL is not reachable at DATABASE_URL — "
            "start it with `docker compose up -d postgres`."
        )


async def _pgcrypto_and_uuid_generation_work() -> tuple[bool, object]:
    engine = create_async_engine(str(get_settings().database_url))
    try:
        async with engine.connect() as connection:
            extension_exists = await connection.scalar(
                text("SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto'")
            )
            generated_uuid = await connection.scalar(text("SELECT gen_random_uuid()"))
    finally:
        await engine.dispose()
    return bool(extension_exists), generated_uuid


def test_upgrading_to_head_enables_pgcrypto_and_gen_random_uuid_works() -> None:
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")

    pgcrypto_enabled, generated_uuid = _run(_pgcrypto_and_uuid_generation_work())

    assert pgcrypto_enabled
    assert generated_uuid is not None


def test_upgrade_is_idempotent_when_already_at_head() -> None:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")

    command.upgrade(config, "head")  # must not raise on a no-op re-run
