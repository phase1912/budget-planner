"""Asking before an account's data goes to the AI (F25.3.2, App Review 5.1.2): allowed or
withdrawn by its owner, and every AI feature waits for it — admins included."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import AiConsentRequiredError
from app.core.config import get_settings
from app.services.quota import QuotaService
from tests.api.test_household import _call
from tests.factories.user import UserFactory

URL = "/users/me/ai-consent"


@pytest.mark.asyncio
async def test_the_owner_allows_the_ai_and_withdraws_it(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(ai_consent_at=None)

    allowed = await _call(db_session, me, "PUT", URL, {"given": True})
    withdrawn = await _call(db_session, me, "PUT", URL, {"given": False})

    assert allowed.status_code == 200 and allowed.json()["ai_consent_at"] is not None
    assert withdrawn.json()["ai_consent_at"] is None


@pytest.mark.asyncio
async def test_allowing_again_keeps_the_day_it_was_first_allowed(
    db_session: AsyncSession,
) -> None:
    first = datetime(2026, 10, 1, tzinfo=UTC)
    me = await UserFactory.create_async(ai_consent_at=first)

    again = await _call(db_session, me, "PUT", URL, {"given": True})

    assert again.json()["ai_consent_at"].startswith("2026-10-01")


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["user", "admin"])
async def test_no_ai_call_is_paid_for_without_the_owners_leave(
    db_session: AsyncSession, role: str
) -> None:
    me = await UserFactory.create_async(ai_consent_at=None, role=role)

    with pytest.raises(AiConsentRequiredError):
        await QuotaService(db_session, get_settings()).ensure_can_spend(
            me, Decimal(1), datetime.now(UTC)
        )


@pytest.mark.asyncio
async def test_the_assistant_waits_for_the_leave_and_says_so(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(ai_consent_at=None)

    response = await _call(
        db_session,
        me,
        "POST",
        "/api/v1/assistant/messages",
        {"text": "how is my month?", "today": "2026-10-20"},
    )

    assert (response.status_code, response.json()["code"]) == (403, "ai_consent_required")
