"""Integration tests for the F0.3 database baseline: Alembic + PostgreSQL (F0.3.2, F0.3.4).

Runs against the isolated per-session test database `tests/conftest.py` builds
(F0.6.1) rather than the shared dev/CI database directly — that fixture already
skips this module when PostgreSQL isn't reachable, and already migrated the
database to `head` once, which is what the first test below is really checking
the effect of.
"""

import asyncio
from collections.abc import Coroutine

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import _migrate_to_head


def _run[T](coro: Coroutine[object, object, T]) -> T:
    return asyncio.run(coro)


async def _pgcrypto_and_uuid_generation_work(database_url: str) -> tuple[bool, object]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            extension_exists = await connection.scalar(
                text("SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto'")
            )
            generated_uuid = await connection.scalar(text("SELECT gen_random_uuid()"))
    finally:
        await engine.dispose()
    return bool(extension_exists), generated_uuid


def test_upgrading_to_head_enables_pgcrypto_and_gen_random_uuid_works(
    test_database_url: str,
) -> None:
    pgcrypto_enabled, generated_uuid = _run(_pgcrypto_and_uuid_generation_work(test_database_url))

    assert pgcrypto_enabled
    assert generated_uuid is not None


def test_upgrade_is_idempotent_when_already_at_head(test_database_url: str) -> None:
    _migrate_to_head(test_database_url)  # must not raise on a re-run against an up-to-date database
