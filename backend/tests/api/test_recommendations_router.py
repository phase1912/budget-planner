"""Asking for advice on a goal, and the advice feed, over HTTP (F8.4, BRD F3, N2)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.routers.recommendations import get_advice_generator
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.domain.advice import AVERAGE_MONTH_DAYS, Advice, AdviceTarget
from app.domain.goal_analysis import GoalAnalysis, analysis_window
from app.domain.goals import GoalType
from app.main import create_app
from app.models.receipt import ReceiptStatus
from app.models.user import User
from app.ports.advice_generation import AdviceUnavailable
from tests.factories.goal import GoalFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

COOKIES = Advice(AdviceTarget.ITEM, "Cookies Choco 300g", "Stop buying them", "9 of 14", 100)
GENERIC = Advice(
    AdviceTarget.CATEGORY, "Discretionary spending", "Consider reducing it", "It adds up", 20
)


class StubAdviceGenerator:
    """Stands in for the model: proposes what it is given, or has no answer at all.

    Records the analysis and currency it was asked with. Honours the port's
    contract: AdviceUnavailable, never another error, when it cannot answer.
    """

    def __init__(self, proposals: list[Advice] | None = None) -> None:
        self.proposals = proposals
        self.asked: list[tuple[GoalAnalysis, str]] = []

    async def propose(self, analysis: GoalAnalysis, currency: str) -> list[Advice]:
        self.asked.append((analysis, currency))
        if self.proposals is None:
            raise AdviceUnavailable
        return self.proposals


async def _call(
    session: AsyncSession,
    user: User,
    method: str,
    path: str,
    generator: StubAdviceGenerator | None = None,
) -> Response:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_advice_generator] = lambda: generator or StubAdviceGenerator([])
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.request(method, f"/api/v1{path}")


async def _shop(
    owner: User,
    item: str,
    *,
    days_ago: int = 0,
    status: ReceiptStatus = ReceiptStatus.PARSED,
) -> None:
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id,
        merchant_name="Fresh Market",
        transaction_date=datetime.now(UTC) - timedelta(days=days_ago),
        status=status,
    )
    await LineItemFactory.create_async(receipt=receipt, name=item, total_price=Decimal("6.80"))


async def _lose_weight(owner: User) -> Any:
    return await GoalFactory.create_async(
        user_id=owner.id,
        type=GoalType.LIFESTYLE,
        financial_kind=None,
        target_amount=None,
        name="Lose weight",
        mapped_item_names=["cookies"],
    )


async def _cookie_eater(**user: Any) -> tuple[User, Any]:
    """A user with enough history for advice (F5) whose receipts show the cookies twice."""
    owner = await UserFactory.create_async(**user)
    for _ in range(2):
        await _shop(owner, "Cookies Choco 300g")
    for _ in range(3):
        await _shop(owner, "Bread", days_ago=40)
    return owner, await _lose_weight(owner)


@pytest.mark.asyncio
async def test_advice_naming_a_purchase_from_the_receipts_is_kept_and_fed(
    db_session: AsyncSession,
) -> None:
    """The demo: a recommendation naming an actual item the user actually buys."""
    user, goal = await _cookie_eater(currency="EUR")
    generator = StubAdviceGenerator([COOKIES])

    advised = await _call(db_session, user, "POST", f"/goals/{goal.id}/recommendations", generator)
    feed = await _call(db_session, user, "GET", "/recommendations")

    assert advised.status_code == 201
    assert [(r["goal_id"], r["target_name"], r["action"]) for r in feed.json()] == [
        (str(goal.id), "Cookies Choco 300g", "Stop buying them")
    ]
    analysis, currency = generator.asked[0]
    assert (analysis.recurring_items[0].receipt_count, currency) == (2, "EUR")


@pytest.mark.asyncio
async def test_generic_advice_is_never_kept(db_session: AsyncSession) -> None:
    """Constraint 11.3: a tip naming nothing from the receipts is a defect, not advice."""
    user, goal = await _cookie_eater()

    advised = await _call(
        db_session,
        user,
        "POST",
        f"/goals/{goal.id}/recommendations",
        StubAdviceGenerator([GENERIC]),
    )

    assert (advised.status_code, advised.json()) == (201, [])


@pytest.mark.asyncio
async def test_asking_again_replaces_a_goals_advice(db_session: AsyncSession) -> None:
    user, goal = await _cookie_eater()
    halve = Advice(AdviceTarget.ITEM, "Cookies Choco 300g", "Halve them", "9 of 14", 50)

    await _call(
        db_session,
        user,
        "POST",
        f"/goals/{goal.id}/recommendations",
        StubAdviceGenerator([COOKIES]),
    )
    await _call(
        db_session, user, "POST", f"/goals/{goal.id}/recommendations", StubAdviceGenerator([halve])
    )
    feed = await _call(db_session, user, "GET", "/recommendations")

    assert [r["action"] for r in feed.json()] == ["Halve them"]


@pytest.mark.asyncio
async def test_a_model_with_no_answer_is_503_and_keeps_the_earlier_advice(
    db_session: AsyncSession,
) -> None:
    user, goal = await _cookie_eater()
    path = f"/goals/{goal.id}/recommendations"

    await _call(db_session, user, "POST", path, StubAdviceGenerator([COOKIES]))
    failed = await _call(db_session, user, "POST", path, StubAdviceGenerator(None))
    feed = await _call(db_session, user, "GET", "/recommendations")

    assert (failed.status_code, failed.json()["code"]) == (503, "advice_unavailable")
    assert [r["action"] for r in feed.json()] == ["Stop buying them"]


@pytest.mark.asyncio
async def test_another_users_goals_and_advice_are_isolated(db_session: AsyncSession) -> None:
    """BRD N2: no advice on their goal, and none of theirs in the feed."""
    owner, goal = await _cookie_eater()
    stranger = await UserFactory.create_async()
    await _call(
        db_session,
        owner,
        "POST",
        f"/goals/{goal.id}/recommendations",
        StubAdviceGenerator([COOKIES]),
    )

    theirs = await _call(db_session, stranger, "POST", f"/goals/{goal.id}/recommendations")
    feed = await _call(db_session, stranger, "GET", "/recommendations")

    assert (theirs.status_code, feed.json()) == (404, [])


@pytest.mark.asyncio
async def test_each_piece_of_advice_carries_what_it_saves_worked_out_from_the_receipts(
    db_session: AsyncSession,
) -> None:
    """BRD F4: the figure comes from the receipts, so it can be checked against them."""
    user, goal = await _cookie_eater()
    halve = Advice(AdviceTarget.ITEM, "Cookies Choco 300g", "Halve them", "9 of 14", 50)

    [advice] = (
        await _call(
            db_session,
            user,
            "POST",
            f"/goals/{goal.id}/recommendations",
            StubAdviceGenerator([halve]),
        )
    ).json()

    window = analysis_window(datetime.now(UTC).date())
    months = Decimal(window.days) / AVERAGE_MONTH_DAYS
    expected = (Decimal("13.60") / months / 2).quantize(Decimal("0.01"), ROUND_HALF_UP)
    assert advice["reduction_percent"] == 50
    assert Decimal(advice["monthly_saving"]) == expected
    assert Decimal(advice["purchases_avoided"]) == (Decimal(2) / months / 2).quantize(
        Decimal("0.1"), ROUND_HALF_UP
    )


@pytest.mark.asyncio
async def test_a_fresh_account_is_told_more_history_is_needed_and_no_model_is_asked(
    db_session: AsyncSession,
) -> None:
    """BRD F5, the demo: three receipts from today are not a pattern."""
    owner = await UserFactory.create_async()
    for _ in range(3):
        await _shop(owner, "Cookies Choco 300g")
    goal = await _lose_weight(owner)
    generator = StubAdviceGenerator([COOKIES])

    advised = await _call(db_session, owner, "POST", f"/goals/{goal.id}/recommendations", generator)
    readiness = await _call(db_session, owner, "GET", "/advice/readiness")

    assert (advised.status_code, advised.json()["code"]) == (422, "insufficient_data")
    assert "you have 3 receipts over 0 days" in advised.json()["detail"]
    assert generator.asked == []
    assert readiness.json() == {
        "ready": False,
        "receipts": 3,
        "required_receipts": 4,
        "history_days": 0,
        "required_days": 30,
        "progress": 0,
    }


@pytest.mark.asyncio
async def test_receipts_held_out_for_review_are_no_history_for_advice(
    db_session: AsyncSession,
) -> None:
    """A receipt that does not count toward the month does not count toward advice (D3)."""
    owner = await UserFactory.create_async()
    await _shop(owner, "Cookies Choco 300g")
    for _ in range(4):
        await _shop(owner, "Bread", days_ago=40, status=ReceiptStatus.MANUAL_REVIEW)

    readiness = (await _call(db_session, owner, "GET", "/advice/readiness")).json()

    assert (readiness["ready"], readiness["receipts"], readiness["history_days"]) == (False, 1, 0)


@pytest.mark.asyncio
async def test_another_users_receipts_are_no_history_for_advice(db_session: AsyncSession) -> None:
    """BRD N2: a stranger's month of shopping does not unlock my advice."""
    await _cookie_eater()
    owner = await UserFactory.create_async()

    readiness = (await _call(db_session, owner, "GET", "/advice/readiness")).json()

    assert (readiness["ready"], readiness["receipts"]) == (False, 0)


@pytest.mark.asyncio
async def test_a_month_of_history_with_enough_receipts_makes_advice_ready(
    db_session: AsyncSession,
) -> None:
    owner, _ = await _cookie_eater()

    readiness = (await _call(db_session, owner, "GET", "/advice/readiness")).json()

    assert (readiness["ready"], readiness["receipts"], readiness["progress"]) == (True, 5, 100)
