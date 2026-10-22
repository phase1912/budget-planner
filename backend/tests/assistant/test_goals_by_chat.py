"""Goals talked about in the chat (F21.5) and answers drawn like the screens (F21.14):
where each goal stands, its advice, what it concerns as a table, the cards themselves —
only ever the caller's own (N2)."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.core.ports import ToolCall
from app.assistant.tools.toolbox import Toolbox
from app.core.config import get_settings
from app.core.context import current_user_id
from app.domain.goals import FinancialKind, GoalType
from app.models.user import User
from app.repository.goal import GoalRepository
from tests.api.test_recommendations_router import COOKIES, StubAdviceGenerator, _shop
from tests.assistant.test_tools import _approve, _propose
from tests.factories.goal import GoalFactory
from tests.factories.user import UserFactory

TODAY = datetime.now(UTC).date()


def _toolbox(session: AsyncSession, user: User, **ports: object) -> Toolbox:
    current_user_id.set(user.id)
    return Toolbox(session, user, TODAY, **ports)  # type: ignore[arg-type]


async def _lose_weight(user: User) -> None:
    await GoalFactory.create_async(
        user_id=user.id,
        type=GoalType.LIFESTYLE,
        financial_kind=None,
        target_amount=None,
        name="Lose weight",
        mapped_item_names=["cookies"],
    )


@pytest.mark.asyncio
async def test_how_my_goals_are_going_comes_with_each_goals_bar(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    other = await UserFactory.create_async()
    await GoalFactory.create_async(
        user_id=me.id,
        financial_kind=FinancialKind.SAVINGS_TARGET,
        name="Holiday",
        target_amount=Decimal("3000"),
        saved_amount=Decimal("1500"),
    )
    await GoalFactory.create_async(user_id=other.id, name="Their goal")
    toolbox = _toolbox(db_session, me)

    figures = json.loads(await toolbox.read(ToolCall("goals", {})))

    [holiday] = figures["goals"]
    assert (holiday["name"], holiday["measure"], holiday["percent"]) == ("Holiday", "savings", 50)
    card = toolbox.answers["goals"].fields
    assert (card["screen"], card["to"], [g["name"] for g in card["goals"]]) == (
        "goals",
        "/goals",
        ["Holiday"],
    )


@pytest.mark.asyncio
async def test_which_products_to_drop_for_a_goal_is_a_table_of_what_it_concerns(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async()
    await _lose_weight(me)
    for _ in range(2):
        await _shop(me, "Cookies Choco 300g")
    await _shop(me, "Milk")
    toolbox = _toolbox(db_session, me)

    figures = json.loads(await toolbox.read(ToolCall("goal_products", {"name": "lose weight"})))

    assert [(p["name"], p["receipts"]) for p in figures["products"]] == [("Cookies Choco 300g", 2)]
    assert toolbox.answers["goal_products"].fields["products"][0]["name"] == "Cookies Choco 300g"


@pytest.mark.asyncio
async def test_fresh_advice_on_a_goal_is_worked_out_as_the_goals_screen_does(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async()
    await _lose_weight(me)
    for _ in range(3):
        await _shop(me, "Cookies Choco 300g", days_ago=40)
    generator = StubAdviceGenerator([COOKIES])
    toolbox = _toolbox(db_session, me, advice=generator)
    settings = get_settings()

    with (
        patch.object(settings, "min_receipts_for_advice", 1),
        patch.object(settings, "min_history_days_for_advice", 1),
    ):
        stored = json.loads(await toolbox.read(ToolCall("goal_advice", {"name": "Lose weight"})))
        fresh = json.loads(
            await toolbox.read(ToolCall("goal_advice", {"name": "Lose weight", "fresh": True}))
        )

    assert stored["advice"] == []
    assert [a["do"] for a in fresh["advice"]] == ["Stop buying them"]
    assert len(generator.asked) == 1


@pytest.mark.asyncio
async def test_a_savings_goal_said_with_a_date_keeps_it(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()
    [card] = await _propose(
        db_session,
        me,
        ToolCall(
            "add_goal",
            {"name": "Holiday", "kind": "savings_target", "amount": "3000", "by": "2027-06-30"},
        ),
    )
    await _approve(db_session, me, card)

    [goal] = await GoalRepository(db_session).list_mine()
    assert (card["card"]["fields"]["by"], str(goal.target_date)) == ("2027-06-30", "2027-06-30")


@pytest.mark.asyncio
async def test_the_cards_answer_shows_the_cards_themselves_and_only_mine(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    other = await UserFactory.create_async()
    for user, name in ((me, "Main"), (other, "Theirs")):
        [card] = await _propose(
            db_session, user, ToolCall("add_account", {"name": name, "balance": "100"})
        )
        await _approve(db_session, user, card)
    toolbox = _toolbox(db_session, me)

    await toolbox.read(ToolCall("accounts", {}))
    await toolbox.read(ToolCall("month_summary", {}))

    accounts = toolbox.answers["accounts"].fields
    assert [(a["name"], a["pays_for_purchases"]) for a in accounts["accounts"]] == [("Main", True)]
    month = toolbox.answers["month_summary"].fields
    assert (month["screen"], month["to"], month["currency"]) == ("month", "/", "PLN")
