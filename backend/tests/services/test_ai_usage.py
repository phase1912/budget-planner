"""Keeping what a model call cost (F21.9.1): one row a call, and a failure never raised."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.metering import Purpose, Spend
from app.models.ai_usage import AiUsage
from app.services.ai_usage import record_usage
from tests.factories.user import UserFactory


@pytest.mark.asyncio
async def test_a_spend_is_kept_as_one_row_of_its_user(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()

    @asynccontextmanager
    async def this_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    with patch("app.services.ai_usage.get_session_factory", lambda: this_session):
        await record_usage(
            Spend(
                Purpose.SPEECH,
                "chirp_3",
                audio_seconds=Decimal("7.5"),
                credits=Decimal("2"),
                user_id=user.id,
            )
        )

    [row] = (await db_session.execute(select(AiUsage).where(AiUsage.user_id == user.id))).scalars()
    assert (row.purpose, row.credits, row.audio_seconds, row.charged) == (
        "speech",
        Decimal("2.000"),
        Decimal("7.50"),
        True,
    )


@pytest.mark.asyncio
async def test_a_failure_to_keep_it_is_logged_not_raised_into_the_call() -> None:
    def broken() -> None:
        raise RuntimeError("database down")

    with patch("app.services.ai_usage.get_session_factory", broken):
        await record_usage(Spend(Purpose.RECEIPT, "m", credits=Decimal(10)))
