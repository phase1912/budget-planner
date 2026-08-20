"""Base class and naming convention for entity test factories (F0.6.3, ADR-0003).

A scenario's `Given` steps should read as business language ("Given a receipt
with 3 line items"), not ORM setup — subclass `ModelFactory` once per entity and
`polyfactory` derives field values from the SQLAlchemy mapping itself.

**Convention:** one file per entity, `tests/factories/<entity_snake_case>.py`,
exposing `<Entity>Factory(ModelFactory[<Entity>])` with `__model__` set. No
entity factory ships with F0.6.3 itself — the epic introducing an entity adds
its factory alongside it (same rule F1.3's cross-user suite follows).
"""

from typing import ClassVar, TypeVar

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Model

ModelT = TypeVar("ModelT", bound=Model)


class ModelFactory(SQLAlchemyFactory[ModelT]):
    """Shared base every entity factory extends instead of `SQLAlchemyFactory` directly.

    `__async_session__` is deliberately left unset here: `tests.conftest.db_session`
    binds it to the current test's session for the lifetime of each test, so a
    concrete factory's `create_async()` persists through — and is rolled back
    with — that test's transaction. A factory used outside `db_session` (i.e.
    with no session bound) can still `.build()` an unpersisted instance.
    """

    __is_base_factory__ = True
    __async_session__: ClassVar[AsyncSession | None] = None
