"""How long a signed-in session lasts (F1.2.2)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.schemas.auth import RefreshRequest
from app.services.auth import AuthService
from tests.factories.user import UserFactory


async def _refreshed_expiry(session: AsyncSession, signed_in_days_ago: int) -> timedelta:
    """Sign in that many days ago, refresh now; how far from now the new token expires."""
    user = await UserFactory.create_async()
    service = AuthService(session)
    _, token = await service._create_session(user.id)
    stored = await session.scalar(select(RefreshToken).where(RefreshToken.token == token))
    assert stored is not None
    now = datetime.now(UTC)
    stored.created_at = now - timedelta(days=signed_in_days_ago)
    stored.expires_at = now + timedelta(days=1)
    await session.flush()

    _, _, renewed = await service.refresh(RefreshRequest(refresh_token=token))
    new = await session.scalar(select(RefreshToken).where(RefreshToken.token == renewed))
    assert new is not None
    return new.expires_at - now


@pytest.mark.asyncio
async def test_using_the_app_keeps_the_session_going_another_thirty_days(
    db_session: AsyncSession,
) -> None:
    remaining = await _refreshed_expiry(db_session, signed_in_days_ago=29)

    assert timedelta(days=29, hours=23) < remaining < timedelta(days=30, minutes=1)


@pytest.mark.asyncio
async def test_no_session_outlives_ninety_days_from_sign_in(db_session: AsyncSession) -> None:
    remaining = await _refreshed_expiry(db_session, signed_in_days_ago=80)

    assert timedelta(days=9, hours=23) < remaining < timedelta(days=10, minutes=1)
