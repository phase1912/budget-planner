"""Every goal shows where it stands, whatever its kind (F8.11, BRD F6, N2)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import current_user_id
from app.domain.accounts import AccountKind
from app.domain.goal_check import GoalCheck, Verdict
from app.domain.goals import FinancialKind, GoalType
from app.services.goal_check import GoalCheckService
from app.services.money_accounts import AccountService
from tests.api.test_goals_router import _call as _goals_call
from tests.api.test_recommendations_router import _call, _shop
from tests.factories.goal import GoalFactory
from tests.factories.user import UserFactory

TODAY = datetime.now(UTC).date()


def _months_ahead(n: int) -> date:
    index = TODAY.year * 12 + TODAY.month - 1 + n
    return date(index // 12, index % 12 + 1, 1)


@pytest.mark.asyncio
async def test_a_savings_goal_counts_what_is_saved_against_its_date(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async()
    goal = await GoalFactory.create_async(
        user_id=owner.id,
        financial_kind=FinancialKind.SAVINGS_TARGET,
        name="Holiday",
        target_amount=Decimal("3000"),
        saved_amount=Decimal("1200"),
        target_date=_months_ahead(8),
    )

    [row] = (await _call(db_session, owner, "GET", "/goals/progress")).json()

    assert (row["goal_id"], row["kind"], row["percent"]) == (str(goal.id), "savings", 40)
    assert Decimal(row["saved"]) == Decimal("1200")
    assert Decimal(row["needed_per_month"]) == Decimal("200.00")
    assert (row["reached"], row["overdue"]) == (False, False)


@pytest.mark.asyncio
async def test_a_savings_goal_on_a_card_counts_what_the_card_holds(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async()
    current_user_id.set(owner.id)
    piggy = await AccountService(db_session).create(
        name="Piggy",
        kind=AccountKind.DEPOSIT,
        opening=Decimal("750"),
        opening_on=TODAY,
        tax_rate=None,
        shared=False,
        for_purchases=False,
    )
    await GoalFactory.create_async(
        user_id=owner.id,
        financial_kind=FinancialKind.SAVINGS_TARGET,
        target_amount=Decimal("1500"),
        saved_account_id=piggy.id,
        saved_amount=Decimal("1"),
    )

    [row] = (await _call(db_session, owner, "GET", "/goals/progress")).json()

    assert (Decimal(row["saved"]), row["percent"]) == (Decimal("750.00"), 50)


@pytest.mark.asyncio
async def test_a_lifestyle_goal_compares_its_watched_lines_with_the_months_before(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async()
    await GoalFactory.create_async(
        user_id=owner.id,
        type=GoalType.LIFESTYLE,
        financial_kind=None,
        target_amount=None,
        name="Lose weight",
        mapped_item_names=["cookies"],
    )
    await _shop(owner, "Cookies Choco", days_ago=0)
    await _shop(owner, "Milk", days_ago=0)
    last_month = (TODAY.replace(day=1) - timedelta(days=10) - TODAY).days * -1
    for _ in range(3):
        await _shop(owner, "Cookies Choco", days_ago=last_month)

    [row] = (await _call(db_session, owner, "GET", "/goals/progress")).json()

    assert row["kind"] == "lifestyle"
    assert Decimal(row["this_month"]) == Decimal("6.80")
    assert Decimal(row["monthly_average"]) == Decimal("6.80")


@pytest.mark.asyncio
async def test_only_a_savings_goal_has_a_date_and_only_ones_own_card_holds_its_money(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async()
    other = await UserFactory.create_async()
    current_user_id.set(other.id)
    theirs = await AccountService(db_session).create(
        name="Theirs",
        kind=AccountKind.DEPOSIT,
        opening=Decimal("9000"),
        opening_on=TODAY,
        tax_rate=None,
        shared=False,
        for_purchases=False,
    )
    saving = {
        "type": "financial",
        "financial_kind": "savings_target",
        "name": "Car",
        "target_amount": "5000",
    }

    dated_ceiling = await _goals_call(
        db_session,
        me,
        "POST",
        "",
        {**saving, "financial_kind": "spending_ceiling", "target_date": "2027-06-30"},
    )
    on_their_card = await _goals_call(
        db_session, me, "POST", "", {**saving, "saved_account_id": str(theirs.id)}
    )
    mine = await _goals_call(db_session, me, "POST", "", {**saving, "target_date": "2027-06-30"})

    assert dated_ceiling.status_code == 422
    assert "Only a savings goal" in dated_ceiling.json()["detail"]
    assert (on_their_card.status_code, on_their_card.json()["detail"]) == (
        422,
        "That card is not one of yours.",
    )
    assert (mine.status_code, mine.json()["target_date"]) == (201, "2027-06-30")


@pytest.mark.asyncio
async def test_a_savings_goal_is_checked_as_what_it_needs_a_month_until_its_date(
    db_session: AsyncSession,
) -> None:
    """3 000 by the first of the month eight months on — nine months, this one counted —
    is judged as 333.33 a month; with no date, over a year."""
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    judged: list[Decimal] = []

    def judge(kind: FinancialKind, target: Decimal, **_: object) -> GoalCheck:
        judged.append(target)
        return GoalCheck(Verdict.DOABLE, Decimal(0), Decimal(0), 3, [])

    with patch("app.services.goal_check.check_goal_plan", judge):
        service = GoalCheckService(db_session)
        await service.check(
            user, FinancialKind.SAVINGS_TARGET, Decimal(3000), None, TODAY, _months_ahead(8)
        )
        await service.check(user, FinancialKind.SAVINGS_TARGET, Decimal(1200), None, TODAY)

    assert judged == [Decimal("333.33"), Decimal("100.00")]
