"""What the family buys, line by line, over HTTP (F12.11, ADR-0017, N2)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.api.test_goal_check import _check
from tests.api.test_household import _call, _household_of
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

URL = "/api/v1/household/lines?start=2026-10-01&end=2026-10-31"


async def _bought(
    owner: User,
    when: datetime,
    name: str,
    price: str,
    *,
    shop: str = "Lidl",
    private: bool = False,
    count: int = 1,
) -> None:
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id,
        merchant_name=shop,
        transaction_date=when,
        total_amount=Decimal(price) * count,
        status=ReceiptStatus.PARSED,
        file_ids=[],
        is_private=private,
    )
    await LineItemFactory.create_async(
        receipt=receipt,
        name=name,
        quantity=Decimal(count),
        unit_price=Decimal(price),
        total_price=Decimal(price) * count,
        category=None,
        position=0,
    )


async def _couple() -> tuple[User, User]:
    me = await UserFactory.create_async(first_name="Bohdan", currency="PLN")
    anna = await UserFactory.create_async(first_name="Anna", currency="PLN")
    await _household_of(me, anna)
    return me, anna


@pytest.mark.asyncio
async def test_the_family_sees_what_two_of_them_bought_twice(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    await _bought(me, datetime(2026, 10, 6, tzinfo=UTC), "Chleb 500g", "5.00")
    await _bought(anna, datetime(2026, 10, 7, tzinfo=UTC), "Chleb 500g", "5.00")

    body = (await _call(db_session, anna, "GET", URL)).json()

    assert [(t["name"], sorted(t["members"]), t["days"]) for t in body["twice"]] == [
        ("Chleb 500g", sorted([str(me.id), str(anna.id)]), ["2026-10-06", "2026-10-07"])
    ]
    assert [(p["name"], len(p["members"])) for p in body["products"]] == [("Chleb 500g", 2)]


@pytest.mark.asyncio
async def test_a_private_receipts_lines_never_reach_the_family(db_session: AsyncSession) -> None:
    """ADR-0017: what is on a private receipt, and when, stays its owner's."""
    me, anna = await _couple()
    await _bought(me, datetime(2026, 10, 6, tzinfo=UTC), "Gift for Anna", "99.00", private=True)

    body = (await _call(db_session, anna, "GET", URL)).json()

    assert body == {"twice": [], "products": []}


@pytest.mark.asyncio
async def test_outside_a_household_there_are_no_family_lines(db_session: AsyncSession) -> None:
    loner = await UserFactory.create_async()

    assert (await _call(db_session, loner, "GET", URL)).status_code == 404


@pytest.mark.asyncio
async def test_a_stretch_goal_names_products_the_family_buys_cheaper_elsewhere(
    db_session: AsyncSession,
) -> None:
    me, anna = await _couple()
    me.usual_income = Decimal("3000.00")
    for month in (7, 8, 9):
        await _bought(
            me, datetime(2026, month, 10, tzinfo=UTC), "Mleko", "4.00", shop="Zabka", count=10
        )
    await _bought(anna, datetime(2026, 9, 2, tzinfo=UTC), "Mleko", "3.00", shop="Lidl")

    body = (
        await _check(
            db_session,
            me,
            {"financial_kind": "spending_ceiling", "target_amount": "20", "today": "2026-10-18"},
        )
    ).json()

    assert body["verdict"] == "stretch"
    assert body["family"] is True
    assert [(s["name"], s["shop"], s["instead_of"]) for s in body["swaps"]] == [
        ("Mleko", "Lidl", "Zabka")
    ]
