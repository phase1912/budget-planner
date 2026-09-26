"""The month figure measured against the user's monthly limit (F6.6, BRD D7)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.api.test_budget_router import _month, _receipt
from tests.factories.user import UserFactory


@pytest.mark.asyncio
async def test_the_month_reads_as_a_share_of_the_limit(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(budget_limit=Decimal("50.00"))
    await _receipt(db_session, user, datetime(2026, 9, 3, tzinfo=UTC), ["40.00"])

    body = (await _month(db_session, user, 2026, 9, today="2026-09-26")).json()

    assert (body["budget_limit"], body["limit_percent"], body["limit_remaining"]) == (
        "50.00",
        80,
        "10.00",
    )


@pytest.mark.asyncio
async def test_a_month_past_its_limit_says_how_far_past(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(budget_limit=Decimal("30.00"))
    await _receipt(db_session, user, datetime(2026, 9, 3, tzinfo=UTC), ["40.00"])

    body = (await _month(db_session, user, 2026, 9, today="2026-09-26")).json()

    assert (body["limit_percent"], body["limit_remaining"]) == (133, "-10.00")


@pytest.mark.asyncio
async def test_without_a_limit_there_is_no_share(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(budget_limit=None)
    await _receipt(db_session, user, datetime(2026, 9, 3, tzinfo=UTC), ["40.00"])

    body = (await _month(db_session, user, 2026, 9, today="2026-09-26")).json()

    assert (body["budget_limit"], body["limit_percent"], body["limit_remaining"]) == (
        None,
        None,
        None,
    )


@pytest.mark.asyncio
async def test_changing_the_limit_remeasures_a_finalised_month_without_rewriting_it(
    db_session: AsyncSession,
) -> None:
    """The limit is presentation only: the snapshot keeps its figure (profile.html)."""
    user = await UserFactory.create_async(budget_limit=Decimal("100.00"))
    await _receipt(db_session, user, datetime(2026, 8, 14, tzinfo=UTC), ["20.00"])
    before = (await _month(db_session, user, 2026, 8, today="2026-09-26")).json()

    user.budget_limit = Decimal("10.00")
    await db_session.flush()
    after = (await _month(db_session, user, 2026, 8, today="2026-09-26")).json()

    assert (before["limit_percent"], after["limit_percent"]) == (20, 200)
    assert (after["total"], after["finalised_at"]) == (before["total"], before["finalised_at"])
