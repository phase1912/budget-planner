import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.api.errors import AuthenticationError, PermissionDeniedError
from app.core.context import current_user_id
from app.repository.base import BaseRepository


class DummyBase(DeclarativeBase):
    pass


class DummyModel(DummyBase):
    __tablename__ = "dummy"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column()
    name: Mapped[str] = mapped_column(String)


class NonOwnedModel(DummyBase):
    __tablename__ = "non_owned"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_repository_applies_ownership_filter_on_get(mock_session: AsyncMock) -> None:
    repo = BaseRepository(DummyModel, mock_session)
    user_id = uuid.uuid4()
    current_user_id.set(user_id)

    await repo.get(uuid.uuid4())

    mock_session.execute.assert_called_once()
    stmt = mock_session.execute.call_args[0][0]
    stmt_str = str(stmt).replace("\n", "")
    assert "dummy.user_id = :user_id_1" in stmt_str or "dummy.user_id = " in stmt_str


@pytest.mark.asyncio
async def test_repository_applies_ownership_filter_on_list(mock_session: AsyncMock) -> None:
    repo = BaseRepository(DummyModel, mock_session)
    user_id = uuid.uuid4()
    current_user_id.set(user_id)

    await repo.list()

    mock_session.execute.assert_called_once()
    stmt = mock_session.execute.call_args[0][0]
    assert "dummy.user_id =" in str(stmt).replace("\n", "")


@pytest.mark.asyncio
async def test_repository_bypasses_ownership_when_explicitly_requested(
    mock_session: AsyncMock,
) -> None:
    repo = BaseRepository(DummyModel, mock_session).bypass_ownership()
    user_id = uuid.uuid4()
    current_user_id.set(user_id)

    await repo.list()

    mock_session.execute.assert_called_once()
    stmt = mock_session.execute.call_args[0][0]
    assert "dummy.user_id =" not in str(stmt).replace("\n", "")


@pytest.mark.asyncio
async def test_repository_ignores_ownership_for_non_owned_models(mock_session: AsyncMock) -> None:
    repo = BaseRepository(NonOwnedModel, mock_session)
    user_id = uuid.uuid4()
    current_user_id.set(user_id)

    await repo.list()

    mock_session.execute.assert_called_once()
    stmt = mock_session.execute.call_args[0][0]
    assert "user_id =" not in str(stmt)


def test_repository_add_assigns_user_id(mock_session: AsyncMock) -> None:
    repo = BaseRepository(DummyModel, mock_session)
    user_id = uuid.uuid4()
    current_user_id.set(user_id)

    dummy = DummyModel(id=uuid.uuid4(), name="Test")
    repo.add(dummy)

    assert dummy.user_id == user_id
    mock_session.add.assert_called_once_with(dummy)


def test_repository_add_fails_on_wrong_user_id(mock_session: AsyncMock) -> None:
    repo = BaseRepository(DummyModel, mock_session)
    user_id = uuid.uuid4()
    current_user_id.set(user_id)

    dummy = DummyModel(id=uuid.uuid4(), user_id=uuid.uuid4(), name="Test")
    with pytest.raises(PermissionDeniedError):
        repo.add(dummy)


def test_repository_requires_context_for_owned_models(mock_session: AsyncMock) -> None:
    repo = BaseRepository(DummyModel, mock_session)
    current_user_id.set(None)

    dummy = DummyModel(id=uuid.uuid4(), name="Test")
    with pytest.raises(AuthenticationError):
        repo.add(dummy)


@pytest.mark.asyncio
async def test_repository_get_requires_context_for_owned_models(mock_session: AsyncMock) -> None:
    repo = BaseRepository(DummyModel, mock_session)
    current_user_id.set(None)

    with pytest.raises(AuthenticationError):
        await repo.get(uuid.uuid4())
