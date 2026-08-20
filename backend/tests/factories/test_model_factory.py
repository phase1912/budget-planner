"""Tests for the entity-factory base class and conventions (F0.6.3).

Exercises the whole pipeline this delivers — `ModelFactory` derives field values
from a SQLAlchemy mapping, and a factory built while `db_session` is active
persists through, and is rolled back with, that test's transaction — against a
throwaway probe entity, since no real domain entity exists yet at E0.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Model
from tests.factories.base import ModelFactory


class _FactoryProbe(Model):
    """A throwaway mapped class used only to exercise `ModelFactory` end to end."""

    __tablename__ = "test_factory_probe"

    name: Mapped[str] = mapped_column(String(100))


_probe_table = Base.metadata.tables["test_factory_probe"]


@pytest.fixture(autouse=True)
def _drop_probe_table_from_metadata_after_test() -> Iterator[None]:
    yield
    Base.metadata.remove(_probe_table)


class _FactoryProbeFactory(ModelFactory[_FactoryProbe]):
    __model__ = _FactoryProbe


def test_build_returns_an_unpersisted_instance_with_generated_field_values() -> None:
    probe = _FactoryProbeFactory.build()

    assert isinstance(probe.name, str)


async def test_create_async_persists_through_the_session_bound_by_db_session(
    db_session: AsyncSession,
) -> None:
    """`db_session` binds `ModelFactory.__async_session__`; a factory needs no session argument."""
    await db_session.run_sync(lambda sync_session: _probe_table.create(sync_session.connection()))

    created = await _FactoryProbeFactory.create_async()

    fetched = await db_session.get(_FactoryProbe, created.id)
    assert fetched is not None
    assert fetched.name == created.name


def test_async_session_is_unbound_outside_a_test_using_db_session() -> None:
    """Guards the fixture's teardown: a factory used with no `db_session` in play must not
    silently reuse a session left over from an earlier test that did request one."""
    assert ModelFactory.__async_session__ is None
