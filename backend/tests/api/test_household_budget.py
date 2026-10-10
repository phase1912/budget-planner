"""A household's month and statistics across its members (F12.5, ADR-0017, BRD N2)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.api.test_household import _call, _household_of
from tests.factories.category import CategoryFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

MONTH = "/api/v1/household/months/2026/10?today=2026-10-15"
STATS = "/api/v1/household/statistics?start=2026-10-01&end=2026-10-31"


async def _spent(
    owner: User,
    amount: str,
    *,
    category: Category | None = None,
    private: bool = False,
    status: ReceiptStatus = ReceiptStatus.PARSED,
    day: int = 5,
) -> None:
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id,
        merchant_name="Shop",
        transaction_date=datetime(2026, 10, day, tzinfo=UTC),
        total_amount=Decimal(amount),
        status=status,
        file_ids=[],
        is_private=private,
    )
    await LineItemFactory.create_async(
        receipt=receipt,
        name="Thing",
        quantity=Decimal(1),
        unit_price=Decimal(amount),
        total_price=Decimal(amount),
        category=category,
        position=0,
    )


async def _couple() -> tuple[User, User]:
    me = await UserFactory.create_async(first_name="Bohdan", currency="PLN")
    anna = await UserFactory.create_async(first_name="Anna", currency="PLN")
    await _household_of(me, anna)
    return me, anna


# --- the month -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_households_month_adds_up_every_members_spend(
    db_session: AsyncSession,
) -> None:
    me, anna = await _couple()
    await _spent(me, "100.00")
    await _spent(anna, "40.00")
    await _spent(anna, "60.00")

    body = (await _call(db_session, me, "GET", MONTH)).json()

    assert Decimal(body["total"]) == Decimal("200.00")
    assert body["receipt_count"] == 3
    split = {m["first_name"]: Decimal(m["total"]) for m in body["members"]}
    assert split == {"Bohdan": Decimal("100.00"), "Anna": Decimal("100.00")}


@pytest.mark.asyncio
async def test_a_private_receipt_counts_as_money_in_its_owners_private_sum(
    db_session: AsyncSession,
) -> None:
    """11h: the household's total is complete, and the receipt says nothing more."""
    me, anna = await _couple()
    await _spent(anna, "30.00")
    await _spent(anna, "120.00", private=True)

    body = (await _call(db_session, me, "GET", MONTH)).json()

    assert Decimal(body["total"]) == Decimal("150.00")
    [anna_share] = [m for m in body["members"] if m["first_name"] == "Anna"]
    assert (Decimal(anna_share["shared_total"]), Decimal(anna_share["private_total"])) == (
        Decimal("30.00"),
        Decimal("120.00"),
    )
    assert "Shop" not in str(body)


@pytest.mark.asyncio
async def test_receipts_under_review_are_held_out_and_named(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    await _spent(me, "10.00")
    await _spent(anna, "99.00", status=ReceiptStatus.MANUAL_REVIEW)

    body = (await _call(db_session, me, "GET", MONTH)).json()

    assert Decimal(body["total"]) == Decimal("10.00")
    assert (body["excluded_count"], Decimal(body["excluded_amount"])) == (1, Decimal("99.00"))


@pytest.mark.asyncio
async def test_other_months_and_strangers_do_not_count(db_session: AsyncSession) -> None:
    me, _anna = await _couple()
    stranger = await UserFactory.create_async()
    await _spent(me, "10.00")
    await ReceiptFactory.create_async(
        user_id=me.id,
        transaction_date=datetime(2026, 9, 30, tzinfo=UTC),
        status=ReceiptStatus.PARSED,
        file_ids=[],
    )
    await _spent(stranger, "500.00")

    body = (await _call(db_session, me, "GET", MONTH)).json()

    assert Decimal(body["total"]) == Decimal("10.00")


@pytest.mark.asyncio
async def test_the_month_is_measured_against_the_household_budget(
    db_session: AsyncSession,
) -> None:
    me, anna = await _couple()
    await _spent(anna, "250.00")

    set_budget = await _call(
        db_session, me, "PUT", "/api/v1/household/budget", {"budget_limit": "1000.00"}
    )
    body = (await _call(db_session, anna, "GET", MONTH)).json()

    assert Decimal(set_budget.json()["budget_limit"]) == Decimal("1000.00")
    assert body["limit"]["percent"] == 25
    assert Decimal(body["limit"]["remaining"]) == Decimal("750.00")


@pytest.mark.asyncio
async def test_only_the_owner_sets_the_household_budget(db_session: AsyncSession) -> None:
    me, anna = await _couple()

    response = await _call(
        db_session, anna, "PUT", "/api/v1/household/budget", {"budget_limit": "5.00"}
    )

    assert response.status_code == 403
    assert (await _call(db_session, me, "GET", MONTH)).json()["limit"] is None


@pytest.mark.asyncio
async def test_a_removed_member_no_longer_counts_or_reads(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    await _spent(anna, "70.00")
    await _call(db_session, me, "DELETE", f"/api/v1/household/members/{anna.id}")

    mine = (await _call(db_session, me, "GET", MONTH)).json()
    hers = await _call(db_session, anna, "GET", MONTH)

    assert Decimal(mine["total"]) == Decimal("0")
    assert hers.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [MONTH, STATS])
async def test_without_a_household_there_is_no_household_view(
    db_session: AsyncSession, url: str
) -> None:
    loner = await UserFactory.create_async()

    response = await _call(db_session, loner, "GET", url)

    assert response.status_code == 404


# --- statistics ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_statistics_show_shared_categories_and_private_as_one_row(
    db_session: AsyncSession,
) -> None:
    me, anna = await _couple()
    groceries = await CategoryFactory.create_async(name="Groceries HH", user_id=None)
    secret = await CategoryFactory.create_async(name="Secret hobby", user_id=anna.id)
    await _spent(me, "60.00", category=groceries)
    await _spent(anna, "20.00", category=groceries)
    await _spent(anna, "20.00", category=secret, private=True)

    body = (await _call(db_session, me, "GET", STATS)).json()

    assert Decimal(body["total"]) == Decimal("100.00")
    assert [(c["name"], Decimal(c["total"]), Decimal(c["share"])) for c in body["categories"]] == [
        ("Groceries HH", Decimal("80.00"), Decimal("80.0"))
    ]
    assert (Decimal(body["private_total"]), Decimal(body["private_share"])) == (
        Decimal("20.00"),
        Decimal("20.0"),
    )
    assert "Secret hobby" not in str(body)


@pytest.mark.asyncio
async def test_a_members_own_category_says_whose_it_is(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    pets = await CategoryFactory.create_async(name="Pets", user_id=anna.id)
    await _spent(anna, "15.00", category=pets)

    [row] = (await _call(db_session, me, "GET", STATS)).json()["categories"]

    assert (row["name"], row["owner_id"]) == ("Pets", str(anna.id))
