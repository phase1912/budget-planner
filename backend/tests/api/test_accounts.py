"""Accounts and the money between them (F23.15, N2)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.household import HouseholdRole
from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.api.test_household import _call, _household_of
from tests.factories.household import HouseholdFactory, HouseholdMemberFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

URL = "/api/v1/accounts"


def on(day: int) -> str:
    return f"?today=2026-10-{day:02d}"


async def _couple() -> tuple[User, User]:
    me = await UserFactory.create_async(first_name="Bohdan", currency="PLN")
    anna = await UserFactory.create_async(first_name="Anna", currency="PLN")
    await _household_of(me, anna)
    return me, anna


async def _open(session: AsyncSession, user: User, day: int = 1, **body: Any) -> dict[str, Any]:
    response = await _call(
        session,
        user,
        "POST",
        f"{URL}{on(day)}",
        {"opening": "0.00", "opening_on": "2026-10-01", **body},
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def _accounts(session: AsyncSession, user: User, day: int) -> dict[str, Any]:
    body = (await _call(session, user, "GET", f"{URL}{on(day)}")).json()
    return {a["name"]: a for a in body["accounts"]} | {"_total": body["total"]}


async def _history(
    session: AsyncSession, user: User, account_id: str, day: int, month: str = "2026-10"
) -> dict[str, Any]:
    return dict(
        (
            await _call(session, user, "GET", f"{URL}/{account_id}/history{on(day)}&month={month}")
        ).json()
    )


async def _receipt(user: User, day: int, amount: str) -> None:
    receipt = await ReceiptFactory.create_async(
        user_id=user.id,
        transaction_date=datetime(2026, 10, day, tzinfo=UTC),
        total_amount=Decimal(amount),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        is_private=False,
    )
    await LineItemFactory.create_async(
        receipt=receipt,
        name="Thing",
        quantity=Decimal(1),
        unit_price=Decimal(amount),
        total_price=Decimal(amount),
        category=None,
    )


@pytest.mark.asyncio
async def test_a_business_account_sets_tax_aside_and_pays_the_family_on_its_day(
    db_session: AsyncSession,
) -> None:
    """The feature's demo: 10 000 from a client is 500 tax and 9 500 clean; ZUS and the
    monthly transfer post themselves on their days."""
    me, _anna = await _couple()
    card = await _open(db_session, me, name="Our card", shared=True)
    business = await _open(
        db_session, me, name="Business", kind="business", tax_rate="5", shared=True
    )
    zus = await _call(
        db_session,
        me,
        "POST",
        f"/api/v1/income/bills{on(5)}",
        {"name": "ZUS", "amount": "1600.00", "day": 20, "account_id": business["id"]},
    )
    assert zus.status_code == 201, zus.text
    rule = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/transfers{on(5)}",
        {
            "from_account_id": business["id"],
            "to_account_id": card["id"],
            "amount": "6000.00",
            "day": 10,
        },
    )
    assert rule.status_code == 201, rule.text
    paid = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/{business['id']}/money-in{on(5)}",
        {"amount": "10000.00", "source": "Acme", "received_on": "2026-10-05"},
    )
    assert paid.status_code == 201, paid.text

    on_the_15th = await _accounts(db_session, me, 15)
    history = await _history(db_session, me, business["id"], 15)
    month = (await _call(db_session, me, "GET", "/api/v1/income?month=2026-10")).json()

    assert Decimal(on_the_15th["Business"]["balance"]) == Decimal("4000.00")
    assert Decimal(on_the_15th["Business"]["set_aside"]) == Decimal("500.00")
    assert Decimal(on_the_15th["Our card"]["balance"]) == Decimal("6000.00")
    assert [(e["name"], e["kind"], e["upcoming"]) for e in history["entries"]] == [
        ("ZUS", "bill", True),
        ("To “Our card”", "transfer_out", False),
        ("Acme", "income", False),
    ]
    assert Decimal(history["entries"][2]["tax"]) == Decimal("500.00")
    # Business income is the family's at once, clean of tax; the transfer is not income.
    assert (Decimal(month["total"]), Decimal(month["net"])) == (
        Decimal("10000.00"),
        Decimal("9500.00"),
    )


@pytest.mark.asyncio
async def test_a_rule_for_a_day_already_past_starts_next_month(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    business = await _open(db_session, me, name="Business", kind="business", tax_rate="5")

    bill = await _call(
        db_session,
        me,
        "POST",
        f"/api/v1/income/bills{on(18)}",
        {"name": "Accountant", "amount": "300.00", "day": 5, "account_id": business["id"]},
    )
    october = await _history(db_session, me, business["id"], 18)
    november = await _history(db_session, me, business["id"], 18, month="2026-11")

    assert bill.json()["starts_on"] == "2026-11-01"
    assert october["entries"] == []
    assert november["entries"] == []  # the future is not posted ahead


@pytest.mark.asyncio
async def test_purchases_come_off_the_family_card_for_every_member(
    db_session: AsyncSession,
) -> None:
    me, anna = await _couple()
    card = await _open(db_session, me, name="Our card", opening="1000.00", shared=True)
    await _receipt(me, 3, "100.00")
    await _receipt(anna, 4, "50.00")

    accounts = await _accounts(db_session, anna, 10)
    history = await _history(db_session, anna, card["id"], 10)

    assert card["for_purchases"] is True
    assert Decimal(accounts["Our card"]["balance"]) == Decimal("850.00")
    assert [(e["kind"], e["author"], e["editable"]) for e in history["entries"]] == [
        ("purchases", None, False),
        ("purchases", "Bohdan", False),
    ]


@pytest.mark.asyncio
async def test_ones_own_card_pays_for_ones_own_purchases_before_the_family_card(
    db_session: AsyncSession,
) -> None:
    me, anna = await _couple()
    await _open(db_session, me, name="Our card", opening="1000.00", shared=True)
    await _open(db_session, anna, name="Anna's card", opening="200.00", for_purchases=True)
    await _receipt(anna, 4, "50.00")

    mine = await _accounts(db_session, me, 10)
    hers = await _accounts(db_session, anna, 10)

    assert Decimal(mine["Our card"]["balance"]) == Decimal("1000.00")
    assert "Anna's card" not in mine
    assert Decimal(hers["Anna's card"]["balance"]) == Decimal("150.00")


@pytest.mark.asyncio
async def test_a_transfer_is_neither_income_nor_spending(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    card = await _open(db_session, me, name="Card", opening="500.00")
    deposit = await _open(db_session, me, name="Deposit", kind="deposit", opening="0.00")

    moved = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/moves{on(10)}",
        {
            "from_account_id": card["id"],
            "to_account_id": deposit["id"],
            "amount": "200.00",
            "moved_on": "2026-10-10",
        },
    )
    accounts = await _accounts(db_session, me, 10)
    balance = (await _call(db_session, me, "GET", "/api/v1/income/balance?today=2026-10-10")).json()

    assert moved.status_code == 201
    assert (accounts["Card"]["balance"], accounts["Deposit"]["balance"]) == ("300.00", "200.00")
    assert (Decimal(balance["balance"]), Decimal(balance["came_in"])) == (
        Decimal("500.00"),
        Decimal("0.00"),
    )


@pytest.mark.asyncio
async def test_an_about_income_waits_to_be_confirmed_and_a_bonus_counts_once(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    business = await _open(db_session, me, name="Business", kind="business", tax_rate="5")
    source = await _call(
        db_session,
        me,
        "POST",
        f"/api/v1/income/regular{on(1)}",
        {
            "name": "Acme",
            "amount": "19167.00",
            "day": 10,
            "about": True,
            "account_id": business["id"],
        },
    )
    source_id = source.json()["id"]

    waiting = (await _call(db_session, me, "GET", f"{URL}/expected{on(12)}")).json()
    before = await _accounts(db_session, me, 12)
    confirmed = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/expected/{source_id}/confirm{on(12)}",
        {"amount": "21400.00"},
    )
    after = await _accounts(db_session, me, 12)
    still_waiting = (await _call(db_session, me, "GET", f"{URL}/expected{on(12)}")).json()

    assert [(w["name"], Decimal(w["amount"])) for w in waiting] == [("Acme", Decimal("19167.00"))]
    assert Decimal(before["Business"]["balance"]) == Decimal("0.00")
    assert confirmed.status_code == 200, confirmed.text
    assert Decimal(confirmed.json()["tax"]) == Decimal("1070.00")
    assert Decimal(after["Business"]["balance"]) == Decimal("21400.00")
    assert still_waiting == []


@pytest.mark.asyncio
async def test_earlier_months_are_closed(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    card = await _open(db_session, me, name="Card", opening="500.00")
    deposit = await _open(db_session, me, name="Deposit", kind="deposit", opening="0.00")

    back_dated = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/moves?today=2026-11-02",
        {
            "from_account_id": card["id"],
            "to_account_id": deposit["id"],
            "amount": "100.00",
            "moved_on": "2026-10-30",
        },
    )

    assert (back_dated.status_code, back_dated.json()["code"]) == (409, "month_closed")


@pytest.mark.asyncio
async def test_a_bill_changed_this_month_stands_in_for_the_rule(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    card = await _open(db_session, me, name="Card", opening="1000.00")
    bill = (
        await _call(
            db_session,
            me,
            "POST",
            f"/api/v1/income/bills{on(1)}",
            {"name": "Internet", "amount": "69.00", "day": 5, "account_id": card["id"]},
        )
    ).json()

    changed = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/occurrences/{bill['id']}{on(10)}",
        {"kind": "bill", "amount": "80.00"},
    )
    history = await _history(db_session, me, card["id"], 10)

    assert changed.status_code == 204, changed.text
    assert [(e["name"], Decimal(e["amount"]), e["ref"]) for e in history["entries"]] == [
        ("Internet", Decimal("-80.00"), "move")
    ]


@pytest.mark.asyncio
async def test_someone_outside_the_household_sees_no_shared_account(
    db_session: AsyncSession,
) -> None:
    """N2: a shared account is the household's; a stranger neither reads nor moves it."""
    me, _anna = await _couple()
    stranger = await UserFactory.create_async(currency="PLN")
    card = await _open(db_session, me, name="Our card", opening="1000.00", shared=True)
    theirs = await _open(db_session, stranger, name="Theirs", opening="0.00")

    listed = await _accounts(db_session, stranger, 10)
    history = await _call(db_session, stranger, "GET", f"{URL}/{card['id']}/history{on(10)}")
    steal = await _call(
        db_session,
        stranger,
        "POST",
        f"{URL}/moves{on(10)}",
        {
            "from_account_id": card["id"],
            "to_account_id": theirs["id"],
            "amount": "1000.00",
            "moved_on": "2026-10-10",
        },
    )

    assert "Our card" not in listed
    assert history.status_code == 404
    assert steal.status_code == 404


@pytest.mark.asyncio
async def test_a_child_sees_the_family_card_but_moves_nothing_on_it(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(first_name="Bohdan", currency="PLN")
    max_ = await UserFactory.create_async(first_name="Max", currency="PLN")
    household = await HouseholdFactory.create_async()
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=me.id, role=HouseholdRole.OWNER.value
    )
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=max_.id, role=HouseholdRole.CHILD.value
    )
    card = await _open(db_session, me, name="Our card", opening="1000.00", shared=True)
    pocket = await _open(db_session, max_, name="Pocket money", opening="0.00")

    seen = await _accounts(db_session, max_, 10)
    take = await _call(
        db_session,
        max_,
        "POST",
        f"{URL}/moves{on(10)}",
        {
            "from_account_id": card["id"],
            "to_account_id": pocket["id"],
            "amount": "1000.00",
            "moved_on": "2026-10-10",
        },
    )

    assert "Our card" in seen
    assert take.json()["code"] == "child_read_only"


@pytest.mark.asyncio
async def test_leaving_takes_ones_shared_account_back(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    await _open(db_session, me, name="Our card", opening="1000.00", shared=True)
    await _open(db_session, anna, name="Her savings", kind="deposit", opening="50.00", shared=True)

    left = await _call(db_session, anna, "POST", "/api/v1/household/leave")
    mine = await _accounts(db_session, me, 10)
    hers = await _accounts(db_session, anna, 10)

    assert left.status_code == 204
    assert "Her savings" not in mine
    assert (hers["Her savings"]["shared"], "Our card" in hers) == (False, False)


@pytest.mark.asyncio
async def test_an_account_read_before_the_day_it_opened_has_only_its_opening(
    db_session: AsyncSession,
) -> None:
    """The caller's own today may fall before an account's opening day (another time zone)."""
    me = await UserFactory.create_async(currency="PLN")
    await _open(db_session, me, name="Card", opening="100.00", opening_on="2026-10-19")

    accounts = await _accounts(db_session, me, 5)

    assert accounts["Card"]["balance"] == "100.00"
