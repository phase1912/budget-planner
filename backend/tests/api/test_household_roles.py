"""Adults and children in a household: who may change what the family shares (F12.10, N2)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdRole
from app.models.user import User
from tests.api.test_household import _call
from tests.factories.household import HouseholdFactory, HouseholdMemberFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

URL = "/api/v1/household"
TODAY = "?today=2026-10-15"


async def _family() -> tuple[User, User, User]:
    """An owner, an adult and a child, in one household."""
    me = await UserFactory.create_async(first_name="Bohdan", currency="PLN")
    anna = await UserFactory.create_async(first_name="Anna", currency="PLN")
    max_ = await UserFactory.create_async(first_name="Max", currency="PLN")
    household = await HouseholdFactory.create_async()
    for user, role in (
        (me, HouseholdRole.OWNER),
        (anna, HouseholdRole.MEMBER),
        (max_, HouseholdRole.CHILD),
    ):
        await HouseholdMemberFactory.create_async(
            household_id=household.id, user_id=user.id, role=role.value
        )
    return me, anna, max_


@pytest.mark.asyncio
async def test_the_owner_marks_a_member_as_a_child_and_back(db_session: AsyncSession) -> None:
    me, anna, _max = await _family()

    child = await _call(db_session, me, "PUT", f"{URL}/members/{anna.id}/role", {"role": "child"})
    adult = await _call(db_session, me, "PUT", f"{URL}/members/{anna.id}/role", {"role": "adult"})

    assert child.status_code == 200
    assert {m["first_name"]: m["role"] for m in child.json()["members"]}["Anna"] == "child"
    assert {m["first_name"]: m["role"] for m in adult.json()["members"]}["Anna"] == "member"


@pytest.mark.asyncio
async def test_only_the_owner_changes_roles_and_the_owner_stays_an_adult(
    db_session: AsyncSession,
) -> None:
    me, anna, max_ = await _family()
    stranger = await UserFactory.create_async()

    by_adult = await _call(
        db_session, anna, "PUT", f"{URL}/members/{max_.id}/role", {"role": "adult"}
    )
    on_owner = await _call(db_session, me, "PUT", f"{URL}/members/{me.id}/role", {"role": "child"})
    outsider = await _call(
        db_session, me, "PUT", f"{URL}/members/{stranger.id}/role", {"role": "child"}
    )

    assert by_adult.json()["code"] == "owner_only"
    assert on_owner.json()["code"] == "owner_role_fixed"
    assert outsider.status_code == 404


@pytest.mark.asyncio
async def test_a_child_sees_the_shared_bill_but_cannot_change_or_stop_it(
    db_session: AsyncSession,
) -> None:
    me, _anna, max_ = await _family()
    flat = await _call(
        db_session,
        me,
        "POST",
        f"/api/v1/income/bills{TODAY}",
        {"name": "Flat", "amount": "3000.00", "day": 5, "shared": True},
    )
    bill_id = flat.json()["id"]

    seen = (await _call(db_session, max_, "GET", "/api/v1/income/bills")).json()
    change = await _call(
        db_session,
        max_,
        "PUT",
        f"/api/v1/income/bills/{bill_id}",
        {"name": "Flat", "amount": "1.00", "day": 5, "shared": True},
    )
    stop = await _call(db_session, max_, "DELETE", f"/api/v1/income/bills/{bill_id}{TODAY}")

    assert [b["name"] for b in seen] == ["Flat"]
    assert (change.status_code, change.json()["code"]) == (403, "child_read_only")
    assert stop.json()["code"] == "child_read_only"


@pytest.mark.asyncio
async def test_a_child_keeps_their_own_money_but_shares_none(db_session: AsyncSession) -> None:
    _me, _anna, max_ = await _family()
    body = {"received_on": "2026-10-10", "amount": "50.00", "source": "Grandma"}

    own = await _call(db_session, max_, "POST", "/api/v1/income", body)
    shared = await _call(db_session, max_, "POST", "/api/v1/income", {**body, "shared": True})

    assert own.status_code == 201
    assert shared.json()["code"] == "child_read_only"


@pytest.mark.asyncio
async def test_a_child_cannot_delete_a_shared_income(db_session: AsyncSession) -> None:
    me, _anna, max_ = await _family()
    salary = await _call(
        db_session,
        me,
        "POST",
        "/api/v1/income",
        {"received_on": "2026-10-10", "amount": "9000.00", "source": "Acme", "shared": True},
    )

    gone = await _call(db_session, max_, "DELETE", f"/api/v1/income/{salary.json()['id']}")

    assert gone.json()["code"] == "child_read_only"


@pytest.mark.asyncio
async def test_a_child_cannot_change_the_household_budget(db_session: AsyncSession) -> None:
    _me, _anna, max_ = await _family()

    response = await _call(db_session, max_, "PUT", f"{URL}/budget", {"budget_limit": "1.00"})

    assert (response.status_code, response.json()["code"]) == (403, "child_read_only")


@pytest.mark.asyncio
async def test_a_kept_budget_is_changed_by_the_owner_alone(db_session: AsyncSession) -> None:
    me, anna, _max = await _family()

    kept = await _call(db_session, me, "PUT", f"{URL}/budget/keeper", {"owner_only": True})
    by_adult = await _call(db_session, anna, "PUT", f"{URL}/budget", {"budget_limit": "900.00"})
    by_owner = await _call(db_session, me, "PUT", f"{URL}/budget", {"budget_limit": "900.00"})
    adult_keeps = await _call(
        db_session, anna, "PUT", f"{URL}/budget/keeper", {"owner_only": False}
    )

    assert kept.json()["owner_sets_budget"] is True
    assert by_adult.json()["code"] == "owner_only"
    assert by_owner.status_code == 200
    assert adult_keeps.json()["code"] == "owner_only"


@pytest.mark.asyncio
async def test_a_childs_receipt_cannot_be_hidden_from_the_family(db_session: AsyncSession) -> None:
    _me, anna, max_ = await _family()
    his = await ReceiptFactory.create_async(user_id=max_.id, file_ids=[])
    hers = await ReceiptFactory.create_async(user_id=anna.id, file_ids=[])

    hidden = await _call(
        db_session, max_, "PUT", f"/receipts/{his.id}/privacy", {"is_private": True}
    )
    adults = await _call(
        db_session, anna, "PUT", f"/receipts/{hers.id}/privacy", {"is_private": True}
    )

    assert hidden.json()["code"] == "child_read_only"
    assert adults.status_code == 200
