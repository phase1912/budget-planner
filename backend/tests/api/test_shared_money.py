"""Money a household shares: incomes and bills seen and changed by every member (F12.8, N2)."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.api.test_household import _call, _household_of
from tests.factories.user import UserFactory

TODAY = "?today=2026-10-15"
MONTH = "/api/v1/income?month=2026-10"


async def _couple() -> tuple[User, User]:
    me = await UserFactory.create_async(first_name="Bohdan", currency="PLN")
    anna = await UserFactory.create_async(first_name="Anna", currency="PLN")
    await _household_of(me, anna)
    return me, anna


async def _bill(session: AsyncSession, user: User, **body: object) -> dict[str, object]:
    response = await _call(
        session,
        user,
        "POST",
        f"/api/v1/income/bills{TODAY}",
        {"name": "Flat", "amount": "3000.00", "day": 5, **body},
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


@pytest.mark.asyncio
async def test_a_shared_bill_is_seen_and_changed_by_the_other_member(
    db_session: AsyncSession,
) -> None:
    me, anna = await _couple()
    flat = await _bill(db_session, me, shared=True)

    hers = (await _call(db_session, anna, "GET", "/api/v1/income/bills")).json()
    changed = await _call(
        db_session,
        anna,
        "PUT",
        f"/api/v1/income/bills/{flat['id']}",
        {"name": "Flat", "amount": "3100.00", "day": 5, "shared": True},
    )
    mine = (await _call(db_session, me, "GET", "/api/v1/income/bills")).json()

    assert [(b["name"], b["shared"], b["mine"], b["added_by"]) for b in hers] == [
        ("Flat", True, False, "Bohdan")
    ]
    assert changed.status_code == 200
    assert [(Decimal(b["amount"]), b["mine"], b["added_by"]) for b in mine] == [
        (Decimal("3100.00"), True, None)
    ]


@pytest.mark.asyncio
async def test_a_bill_kept_to_oneself_stays_unseen_by_the_family(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    gym = await _bill(db_session, me, name="Gym", amount="149.00")

    hers = (await _call(db_session, anna, "GET", "/api/v1/income/bills")).json()
    change = await _call(
        db_session,
        anna,
        "PUT",
        f"/api/v1/income/bills/{gym['id']}",
        {"name": "Gym", "amount": "1.00", "day": 5},
    )

    assert hers == []
    assert change.status_code == 404


@pytest.mark.asyncio
async def test_someone_outside_the_household_sees_and_changes_nothing_shared(
    db_session: AsyncSession,
) -> None:
    """N2: sharing widens access to the household's members only."""
    me, _anna = await _couple()
    stranger = await UserFactory.create_async()
    flat = await _bill(db_session, me, shared=True)

    seen = (await _call(db_session, stranger, "GET", "/api/v1/income/bills")).json()
    stop = await _call(db_session, stranger, "DELETE", f"/api/v1/income/bills/{flat['id']}{TODAY}")

    assert seen == []
    assert stop.status_code == 404


@pytest.mark.asyncio
async def test_a_shared_bill_is_the_familys_whole_never_divided_into_parts(
    db_session: AsyncSession,
) -> None:
    """ADR-0023: it comes out of the shared budget once, so nobody is shown a part."""
    me, anna = await _couple()
    await _bill(db_session, me, shared=True)

    mine = (await _call(db_session, me, "GET", "/api/v1/income/bills")).json()[0]
    hers = (await _call(db_session, anna, "GET", "/api/v1/income/bills")).json()[0]

    assert Decimal(mine["amount"]) == Decimal(hers["amount"]) == Decimal("3000.00")
    assert "my_part" not in hers and "split" not in hers


@pytest.mark.asyncio
async def test_a_shared_income_counts_in_every_members_month(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    response = await _call(
        db_session,
        me,
        "POST",
        "/api/v1/income",
        {"received_on": "2026-10-10", "amount": "9000.00", "source": "Acme", "shared": True},
    )
    assert response.status_code == 201

    hers = (await _call(db_session, anna, "GET", MONTH)).json()

    assert Decimal(hers["total"]) == Decimal("9000.00")
    assert [(e["source"], e["shared"], e["added_by"]) for e in hers["entries"]] == [
        ("Acme", True, "Bohdan")
    ]


@pytest.mark.asyncio
async def test_sharing_needs_a_household(db_session: AsyncSession) -> None:
    loner = await UserFactory.create_async()

    response = await _call(
        db_session,
        loner,
        "POST",
        f"/api/v1/income/bills{TODAY}",
        {"name": "Flat", "amount": "3000.00", "shared": True},
    )

    assert response.json()["code"] == "not_in_household"


@pytest.mark.asyncio
async def test_leaving_takes_ones_shared_money_back_and_leaves_the_others(
    db_session: AsyncSession,
) -> None:
    me, anna = await _couple()
    await _bill(db_session, me, shared=True)
    await _bill(db_session, anna, name="Internet", amount="69.00", shared=True)

    left = await _call(db_session, anna, "POST", "/api/v1/household/leave")
    hers = (await _call(db_session, anna, "GET", "/api/v1/income/bills")).json()
    mine = (await _call(db_session, me, "GET", "/api/v1/income/bills")).json()

    assert left.status_code == 204
    assert [(b["name"], b["shared"]) for b in hers] == [("Internet", False)]
    assert [(b["name"], b["shared"]) for b in mine] == [("Flat", True)]
