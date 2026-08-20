"""Tests for the per-test transactional rollback isolation `db_session` provides (F0.6.1).

Two tests, in file order, against the same throwaway table: if a previous
test's write survived, the second test would see it. `_ensure_probe_table` has
to run in every test rather than once, because the table itself is created
inside the test's transaction and is rolled back along with everything else —
which is itself evidence the rollback works, not just the row-level assertion
below it.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Model


class _IsolationProbe(Model):
    """A throwaway mapped class used only to prove rollback-per-test isolation."""

    __tablename__ = "test_isolation_probe"

    name: Mapped[str] = mapped_column(String(100))


_probe_table = Base.metadata.tables["test_isolation_probe"]


@pytest.fixture(autouse=True, scope="module")
def _drop_probe_table_from_metadata_after_module() -> Iterator[None]:
    yield
    Base.metadata.remove(_probe_table)


async def _ensure_probe_table(session: AsyncSession) -> None:
    await session.run_sync(lambda sync_session: _probe_table.create(sync_session.connection()))


async def test_insert_leaves_no_trace_for_a_later_test(db_session: AsyncSession) -> None:
    await _ensure_probe_table(db_session)
    existing = (await db_session.execute(select(_IsolationProbe))).scalars().all()
    assert existing == []

    db_session.add(_IsolationProbe(name="should not leak into the next test"))
    await db_session.commit()  # a savepoint release, not a real commit — see conftest.db_session


async def test_a_later_test_does_not_see_the_earlier_insert(db_session: AsyncSession) -> None:
    await _ensure_probe_table(db_session)
    existing = (await db_session.execute(select(_IsolationProbe))).scalars().all()
    assert existing == []
