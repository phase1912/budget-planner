"""Advice waiting on goals at risk before the user asks (BRD F7 — F8.8)."""

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# app.services.advice imports app.api.errors, whose package imports every router,
# one of which imports app.services.advice: load the package first to break the cycle.
import app.api  # noqa: F401
from app.core.context import current_user_id
from app.domain.advice import Advice, AdviceTarget
from app.domain.goal_analysis import GoalAnalysis
from app.models.receipt import ReceiptStatus
from app.models.user import User
from app.ports.advice_generation import AdviceUnavailable
from app.repository.recommendation import RecommendationRepository
from app.services.advice import build_advice_service
from app.services.proactive_advice import run_every
from tests.factories.goal import GoalFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

AS_OF = date(2026, 9, 20)
COOKIES = Advice(AdviceTarget.ITEM, "Cookies Choco 300g", "Stop buying them", "9 of 14", 100)


class StubAdviceGenerator:
    """Stands in for the model: proposes what it is given, or has no answer at all."""

    def __init__(self, proposals: list[Advice] | None) -> None:
        self.proposals = proposals
        self.asked = 0

    async def propose(self, analysis: GoalAnalysis, currency: str) -> list[Advice]:
        self.asked += 1
        if self.proposals is None:
            raise AdviceUnavailable
        return self.proposals


async def _shop(owner: User, on: date, amount: str = "6.80") -> None:
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id,
        merchant_name="Fresh Market",
        transaction_date=datetime(on.year, on.month, on.day, 12, tzinfo=UTC),
        status=ReceiptStatus.PARSED,
    )
    await LineItemFactory.create_async(
        receipt=receipt, name="Cookies Choco 300g", total_price=Decimal(amount)
    )


async def _spender(**goal: Any) -> tuple[User, Any]:
    """A month of history (F5), then 100 PLN of cookies twice this month by the 20th."""
    owner = await UserFactory.create_async()
    current_user_id.set(owner.id)
    for day in (1, 5, 10):
        await _shop(owner, date(2026, 8, day))
    await _shop(owner, date(2026, 9, 2), "100.00")
    await _shop(owner, date(2026, 9, 15), "100.00")
    return owner, await GoalFactory.create_async(user_id=owner.id, **goal)


def _service(session: AsyncSession, generator: StubAdviceGenerator) -> Any:
    return build_advice_service(session, generator, required_receipts=4, required_days=30)


@pytest.mark.asyncio
async def test_a_goal_heading_over_its_cap_gets_advice_without_asking(
    db_session: AsyncSession,
) -> None:
    """The demo: 200 PLN by the 20th heads to 300 against a 250 ceiling."""
    owner, goal = await _spender(target_amount=Decimal("250"))
    generator = StubAdviceGenerator([COOKIES])

    prepared = await _service(db_session, generator).prepare_for_goals_at_risk(AS_OF, "PLN")

    advice = await RecommendationRepository(db_session).list_mine()
    assert (prepared, generator.asked) == (1, 1)
    assert [(a.goal_id, a.action) for a in advice] == [(goal.id, "Stop buying them")]
    assert {a.user_id for a in advice} == {owner.id}


@pytest.mark.asyncio
async def test_a_goal_on_track_is_left_alone(db_session: AsyncSession) -> None:
    await _spender(target_amount=Decimal("1000"))
    generator = StubAdviceGenerator([COOKIES])

    prepared = await _service(db_session, generator).prepare_for_goals_at_risk(AS_OF, "PLN")

    assert (prepared, generator.asked) == (0, 0)


@pytest.mark.asyncio
async def test_advice_already_given_this_month_is_never_overwritten(
    db_session: AsyncSession,
) -> None:
    """The user's own advice stays, and the model is asked once per goal per month."""
    _, goal = await _spender(target_amount=Decimal("250"))
    asked_by_user = StubAdviceGenerator([COOKIES])
    await _service(db_session, asked_by_user).advise(goal.id, as_of=AS_OF, currency="PLN")
    background = StubAdviceGenerator([COOKIES])

    prepared = await _service(db_session, background).prepare_for_goals_at_risk(AS_OF, "PLN")

    assert (prepared, background.asked) == (0, 0)


@pytest.mark.asyncio
async def test_a_model_with_no_answer_skips_the_goal_and_carries_on(
    db_session: AsyncSession,
) -> None:
    await _spender(target_amount=Decimal("250"))

    prepared = await _service(db_session, StubAdviceGenerator(None)).prepare_for_goals_at_risk(
        AS_OF, "PLN"
    )

    assert prepared == 0


@pytest.mark.asyncio
async def test_too_little_history_prepares_nothing(db_session: AsyncSession) -> None:
    owner = await UserFactory.create_async()
    current_user_id.set(owner.id)
    await _shop(owner, date(2026, 9, 15), "500.00")
    await GoalFactory.create_async(user_id=owner.id, target_amount=Decimal("100"))
    generator = StubAdviceGenerator([COOKIES])

    prepared = await _service(db_session, generator).prepare_for_goals_at_risk(AS_OF, "PLN")

    assert (prepared, generator.asked) == (0, 0)


@pytest.mark.asyncio
async def test_the_schedule_keeps_running_after_a_failed_pass() -> None:
    calls: list[date] = []

    async def one_pass(as_of: date) -> int:
        calls.append(as_of)
        if len(calls) == 1:
            raise RuntimeError("database away")
        return 0

    task = asyncio.create_task(run_every(0.01, one_pass, first_delay_seconds=0))
    await asyncio.sleep(0.05)
    task.cancel()

    assert len(calls) >= 2
