"""Stating, changing and dropping goals over HTTP (F8.1, F8.2, BRD F1, F9, N2)."""

from collections.abc import AsyncGenerator, Sequence
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.routers.goals import get_goal_mapper
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.domain.goals import GoalType
from app.main import create_app
from app.models.category import Category
from app.models.user import User
from app.ports.goal_mapping import GoalMappingResult
from tests.factories.category import CategoryFactory
from tests.factories.goal import GoalFactory
from tests.factories.user import UserFactory

CEILING = {
    "type": "financial",
    "financial_kind": "spending_ceiling",
    "name": "Stay under 3 000 PLN a month",
    "target_amount": "3000.00",
}


class StubGoalMapper:
    """Stands in for the model: watches "Snacks" when offered, and "sweets".

    Honours the port's contract — only offered categories come back, never raises —
    and records each goal it was asked about, so a test can tell whether it ran.
    """

    def __init__(self) -> None:
        self.asked: list[str] = []

    async def map_goal(
        self, name: str, description: str | None, categories: Sequence[Category]
    ) -> GoalMappingResult:
        self.asked.append(name)
        return GoalMappingResult(
            mapped_category_ids=[c.id for c in categories if c.name == "Snacks"],
            mapped_item_names=["sweets"],
        )


async def _call(
    session: AsyncSession,
    user: User,
    method: str,
    path: str,
    body: Any = None,
    mapper: StubGoalMapper | None = None,
) -> Response:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_goal_mapper] = lambda: mapper or StubGoalMapper()
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.request(method, f"/api/v1/goals{path}", json=body)


@pytest.mark.asyncio
async def test_a_money_goal_and_a_lifestyle_goal_are_both_stated_and_listed(
    db_session: AsyncSession,
) -> None:
    """The demo: "stay under 3 000 PLN a month" and "lose weight", both on the screen."""
    user = await UserFactory.create_async()

    ceiling = await _call(db_session, user, "POST", "", CEILING)
    lifestyle = await _call(
        db_session, user, "POST", "", {"type": "lifestyle", "name": "  Lose weight  "}
    )
    listed = await _call(db_session, user, "GET", "")

    assert (ceiling.status_code, lifestyle.status_code) == (201, 201)
    assert lifestyle.json()["name"] == "Lose weight"
    # Both are stated in one test transaction, so they share a timestamp: compare as a set.
    assert {(g["name"], g["financial_kind"], g["target_amount"]) for g in listed.json()} == {
        ("Lose weight", None, None),
        ("Stay under 3 000 PLN a month", "spending_ceiling", "3000.00"),
    }


@pytest.mark.asyncio
async def test_a_goal_can_be_edited_and_dropped(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    goal = await GoalFactory.create_async(user_id=user.id)

    edited = await _call(
        db_session,
        user,
        "PATCH",
        f"/{goal.id}",
        {"name": "Stay under 2 500", "target_amount": "2500"},
    )
    dropped = await _call(db_session, user, "DELETE", f"/{goal.id}")
    listed = await _call(db_session, user, "GET", "")

    assert (edited.json()["name"], edited.json()["target_amount"]) == (
        "Stay under 2 500",
        "2500.00",
    )
    assert (dropped.status_code, listed.json()) == (204, [])


@pytest.mark.asyncio
async def test_a_goal_cutting_one_category_names_one_the_user_can_use(
    db_session: AsyncSession,
) -> None:
    """Their own or a built-in category, never another user's custom one (N2)."""
    user = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    mine = await CategoryFactory.create_async(name="Takeaway", user_id=user.id)
    theirs = await CategoryFactory.create_async(name="Their secret", user_id=stranger.id)
    cut = {**CEILING, "financial_kind": "category_reduction", "name": "Less takeaway"}

    ok = await _call(db_session, user, "POST", "", {**cut, "category_id": str(mine.id)})
    refused = await _call(db_session, user, "POST", "", {**cut, "category_id": str(theirs.id)})

    assert (ok.status_code, ok.json()["category_id"]) == (201, str(mine.id))
    assert (refused.status_code, refused.json()["code"]) == (422, "invalid_goal")
    assert refused.json()["detail"] == "That category is not one of yours."


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ({**CEILING, "target_amount": "-5"}, "A money goal needs an amount above zero."),
        ({**CEILING, "financial_kind": None}, "Say what kind of money goal this is."),
        (
            {"type": "lifestyle", "name": "Lose weight", "target_amount": "10"},
            "A lifestyle goal has no amount, kind or category.",
        ),
    ],
)
@pytest.mark.asyncio
async def test_a_malformed_goal_is_refused_with_the_reason(
    db_session: AsyncSession, body: dict[str, Any], detail: str
) -> None:
    user = await UserFactory.create_async()
    response = await _call(db_session, user, "POST", "", body)
    assert (response.status_code, response.json()["detail"]) == (422, detail)


@pytest.mark.asyncio
async def test_an_edit_cannot_clear_a_name_or_break_the_goal(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    goal = await GoalFactory.create_async(user_id=user.id)

    no_name = await _call(db_session, user, "PATCH", f"/{goal.id}", {"name": None})
    no_amount = await _call(db_session, user, "PATCH", f"/{goal.id}", {"target_amount": None})

    assert (no_name.status_code, no_name.json()["detail"]) == (422, "A goal needs a name.")
    assert (no_amount.status_code, no_amount.json()["code"]) == (422, "invalid_goal")


@pytest.mark.asyncio
async def test_another_users_goals_are_isolated(db_session: AsyncSession) -> None:
    """BRD N2: not listed, and neither changed nor dropped — each reads as not found."""
    owner = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    goal = await GoalFactory.create_async(user_id=owner.id)

    listed = await _call(db_session, stranger, "GET", "")
    patched = await _call(db_session, stranger, "PATCH", f"/{goal.id}", {"name": "Hacked"})
    dropped = await _call(db_session, stranger, "DELETE", f"/{goal.id}")

    assert listed.json() == []
    assert (patched.status_code, dropped.status_code) == (404, 404)


LOSE_WEIGHT = {"type": "lifestyle", "name": "Lose weight", "description": "Fewer snacks"}


@pytest.mark.asyncio
async def test_a_lifestyle_goal_is_stated_with_the_spending_lines_it_watches(
    db_session: AsyncSession,
) -> None:
    """BRD F9: the goal is projected onto spending before any advice is built."""
    user = await UserFactory.create_async()
    snacks = await CategoryFactory.create_async(name="Snacks", user_id=user.id)
    mapper = StubGoalMapper()

    stated = await _call(db_session, user, "POST", "", LOSE_WEIGHT, mapper)

    assert stated.json()["mapped_category_ids"] == [str(snacks.id)]
    assert stated.json()["mapped_item_names"] == ["sweets"]
    assert mapper.asked == ["Lose weight"]


@pytest.mark.asyncio
async def test_a_money_goal_is_never_sent_to_the_mapper(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    mapper = StubGoalMapper()

    stated = await _call(db_session, user, "POST", "", CEILING, mapper)

    assert (stated.json()["mapped_item_names"], mapper.asked) == ([], [])


@pytest.mark.asyncio
async def test_rewording_a_lifestyle_goal_maps_it_again_but_saving_it_unchanged_does_not(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    goal = await GoalFactory.create_async(
        user_id=user.id,
        type=GoalType.LIFESTYLE,
        financial_kind=None,
        target_amount=None,
        name="Lose weight",
    )
    mapper = StubGoalMapper()

    await _call(db_session, user, "PATCH", f"/{goal.id}", {"name": "Lose weight"}, mapper)
    reworded = await _call(
        db_session, user, "PATCH", f"/{goal.id}", {"description": "No sugar"}, mapper
    )

    assert mapper.asked == ["Lose weight"]
    assert reworded.json()["mapped_item_names"] == ["sweets"]


@pytest.mark.asyncio
async def test_the_users_correction_of_what_a_goal_watches_survives_a_rewording(
    db_session: AsyncSession,
) -> None:
    """The user's list is theirs: no automatic pass overwrites it (cf. BRD C4)."""
    user = await UserFactory.create_async()
    goal = await GoalFactory.create_async(
        user_id=user.id, type=GoalType.LIFESTYLE, financial_kind=None, target_amount=None
    )
    mapper = StubGoalMapper()

    corrected = await _call(
        db_session,
        user,
        "PATCH",
        f"/{goal.id}",
        {"mapped_item_names": [" Beer ", "beer", "Crisps"]},
        mapper,
    )
    reworded = await _call(
        db_session, user, "PATCH", f"/{goal.id}", {"description": "Drink less"}, mapper
    )

    assert corrected.json()["mapped_item_names"] == ["beer", "crisps"]
    assert reworded.json()["mapped_item_names"] == ["beer", "crisps"]
    assert mapper.asked == []


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ({"mapped_item_names": None}, "Send an empty list to stop watching every item."),
        ({"mapped_category_ids": None}, "Send an empty list to stop watching every category."),
        ({"mapped_category_ids": "THEIRS"}, "That category is not one of yours."),
    ],
)
@pytest.mark.asyncio
async def test_a_correction_that_would_break_a_lifestyle_goal_is_refused(
    db_session: AsyncSession, body: dict[str, Any], detail: str
) -> None:
    """Including another user's custom category, which is not theirs to watch (N2)."""
    user = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    theirs = await CategoryFactory.create_async(name="Their secret", user_id=stranger.id)
    goal = await GoalFactory.create_async(
        user_id=user.id, type=GoalType.LIFESTYLE, financial_kind=None, target_amount=None
    )
    if body.get("mapped_category_ids") == "THEIRS":
        body = {"mapped_category_ids": [str(theirs.id)]}

    response = await _call(db_session, user, "PATCH", f"/{goal.id}", body)

    assert (response.status_code, response.json()["detail"]) == (422, detail)


@pytest.mark.asyncio
async def test_a_money_goal_cannot_be_given_spending_lines_to_watch(
    db_session: AsyncSession,
) -> None:
    """Keeping the two goal types apart is what BRD F9 relies on."""
    user = await UserFactory.create_async()
    goal = await GoalFactory.create_async(user_id=user.id)

    response = await _call(
        db_session, user, "PATCH", f"/{goal.id}", {"mapped_item_names": ["beer"]}
    )

    assert (response.status_code, response.json()["detail"]) == (
        422,
        "Only a lifestyle goal watches spending lines.",
    )


@pytest.mark.asyncio
async def test_an_overlong_item_name_is_refused(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    goal = await GoalFactory.create_async(
        user_id=user.id, type=GoalType.LIFESTYLE, financial_kind=None, target_amount=None
    )

    response = await _call(
        db_session, user, "PATCH", f"/{goal.id}", {"mapped_item_names": ["x" * 121]}
    )

    assert response.status_code == 422
