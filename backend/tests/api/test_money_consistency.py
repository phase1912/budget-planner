"""Every screen tells the same money story (F23.10-F23.18, F12.8, F23.15).

Home's balance, Plan's month, the accounts and their histories are computed by different
services; these tests build realistic months and check that they never disagree. They use
the real current month, because only this month's entries can be written once there are
accounts.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.api.test_household import _call, _household_of
from tests.factories.income_source import IncomeSourceFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

TODAY = datetime.now(UTC).date()
MONTH = TODAY.replace(day=1)
Q = f"?today={TODAY.isoformat()}"


def _money(value: Any) -> Decimal:
    return Decimal(str(value))


async def _post(session: AsyncSession, user: User, url: str, body: dict[str, Any]) -> Any:
    response = await _call(session, user, "POST", url, body)
    assert response.status_code in (200, 201), response.text
    return response.json() if response.content else None


async def _bought(user: User, amount: str) -> None:
    """A receipt read today, counted in the month (D1-D3)."""
    receipt = await ReceiptFactory.create_async(
        user_id=user.id,
        transaction_date=datetime.combine(MONTH, datetime.min.time(), UTC),
        total_amount=Decimal(amount),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        is_private=False,
    )
    await LineItemFactory.create_async(
        receipt=receipt,
        name="Groceries",
        quantity=Decimal(1),
        unit_price=Decimal(amount),
        total_price=Decimal(amount),
        category=None,
    )


async def _views(session: AsyncSession, user: User) -> dict[str, Any]:
    accounts = (await _call(session, user, "GET", f"/api/v1/accounts{Q}")).json()
    balance = (await _call(session, user, "GET", f"/api/v1/income/balance{Q}")).json()
    month = (await _call(session, user, "GET", f"/api/v1/income?month={MONTH:%Y-%m}")).json()
    return {"accounts": accounts, "balance": balance, "month": month}


@pytest.mark.asyncio
async def test_a_familys_month_adds_up_the_same_on_every_screen(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(first_name="Bohdan", currency="PLN")
    anna = await UserFactory.create_async(first_name="Anna", currency="PLN")
    await _household_of(me, anna)
    card = await _post(
        db_session,
        me,
        f"/api/v1/accounts{Q}",
        {
            "name": "Our card",
            "opening": "1000.00",
            "opening_on": MONTH.isoformat(),
            "shared": True,
            "for_purchases": True,
        },
    )
    business = await _post(
        db_session,
        me,
        f"/api/v1/accounts{Q}",
        {
            "name": "Business",
            "kind": "business",
            "opening": "0.00",
            "opening_on": MONTH.isoformat(),
            "tax_rate": "5",
            "shared": True,
        },
    )
    # Money in from a client: 5 % set aside, the rest the family's income at once.
    await _post(
        db_session,
        me,
        f"/api/v1/accounts/{business['id']}/money-in{Q}",
        {"amount": "10000.00", "source": "Acme", "received_on": MONTH.isoformat()},
    )
    # What the family pays itself: a transfer, neither income nor spending.
    before_move = await _views(db_session, me)
    await _post(
        db_session,
        me,
        f"/api/v1/accounts/moves{Q}",
        {
            "from_account_id": business["id"],
            "to_account_id": card["id"],
            "amount": "6000.00",
            "moved_on": MONTH.isoformat(),
        },
    )
    await _post(
        db_session,
        anna,
        f"/api/v1/income/bills{Q}",
        {
            "name": "Flat",
            "amount": "3000.00",
            "day": TODAY.day,
            "shared": True,
            "account_id": card["id"],
        },
    )
    await _bought(me, "120.00")
    await _bought(anna, "80.00")

    views = await _views(db_session, me)
    hers = await _views(db_session, anna)
    accounts = {a["name"]: a for a in views["accounts"]["accounts"]}

    # Home's balance is the money on every account the user sees.
    assert _money(views["balance"]["balance"]) == _money(views["accounts"]["total"])
    assert _money(hers["balance"]["balance"]) == _money(hers["accounts"]["total"])
    # 1000 + 10000 - 3000 rent - 200 purchases; the 6000 only moved.
    assert _money(views["accounts"]["total"]) == Decimal("7800.00")
    assert _money(accounts["Business"]["balance"]) == Decimal("4000.00")
    assert _money(accounts["Our card"]["balance"]) == Decimal("3800.00")
    # The tax set aside is the month's tax, and what the balance owes the tax office.
    assert _money(views["month"]["taxes"]) == _money(accounts["Business"]["set_aside"])
    assert _money(views["balance"]["for_taxes"]) == Decimal("500.00")
    # The transfer changed neither the month's income nor the money in all.
    assert _money(views["month"]["total"]) == _money(before_move["month"]["total"])
    assert _money(views["month"]["total"]) == Decimal("10000.00")
    assert _money(views["month"]["net"]) == Decimal("9500.00")
    # The family's shared bill counts once, whole, for both of them.
    assert _money(views["month"]["bills_total"]) == _money(hers["month"]["bills_total"])


@pytest.mark.asyncio
async def test_moving_from_a_starting_balance_to_accounts_moves_no_figure(
    db_session: AsyncSession,
) -> None:
    """The first income opens the purchase card with the balance as it was started."""
    me = await UserFactory.create_async(
        currency="PLN", starting_balance=Decimal("2500.00"), balance_since=MONTH
    )
    await _bought(me, "300.00")
    before = (await _call(db_session, me, "GET", f"/api/v1/income/balance{Q}")).json()

    await _post(
        db_session,
        me,
        "/api/v1/income",
        {"received_on": TODAY.isoformat(), "amount": "700.00", "source": "Gift", "kind": "other"},
    )
    after = (await _call(db_session, me, "GET", f"/api/v1/income/balance{Q}")).json()

    assert (before["from_accounts"], after["from_accounts"]) == (False, True)
    assert _money(before["balance"]) == Decimal("2200.00")
    assert _money(after["balance"]) == _money(before["balance"]) + Decimal("700.00")


@pytest.mark.asyncio
async def test_changing_a_regular_income_never_rewrites_last_month(
    db_session: AsyncSession,
) -> None:
    """A rule is read for every month it runs: a change starts a new version from now."""
    me = await UserFactory.create_async(currency="PLN")
    last_month = (MONTH - timedelta(days=1)).replace(day=1)
    salary = await IncomeSourceFactory.create_async(
        user_id=me.id, amount=Decimal("9000.00"), day=10, starts_on=last_month
    )
    url = f"/api/v1/income?month={last_month:%Y-%m}"
    before = (await _call(db_session, me, "GET", url)).json()

    changed = await _call(
        db_session,
        me,
        "PUT",
        f"/api/v1/income/regular/{salary.id}",
        {"name": "Salary", "amount": "10000.00", "day": 10},
    )
    after_last = (await _call(db_session, me, "GET", url)).json()
    this_month = (await _call(db_session, me, "GET", f"/api/v1/income?month={MONTH:%Y-%m}")).json()
    listed = (await _call(db_session, me, "GET", "/api/v1/income/regular")).json()

    assert changed.status_code == 200, changed.text
    assert _money(before["total"]) == _money(after_last["total"]) == Decimal("9000.00")
    assert _money(this_month["total"]) == Decimal("10000.00")
    assert [(r["name"], _money(r["amount"])) for r in listed] == [("Salary", Decimal("10000.00"))]


@pytest.mark.asyncio
async def test_one_person_without_a_family_or_a_card_gets_one_story(
    db_session: AsyncSession,
) -> None:
    """Alone, with no household and no accounts: income, a bill and purchases agree."""
    me = await UserFactory.create_async(currency="PLN", language="pl")
    await _post(
        db_session,
        me,
        f"/api/v1/income/regular{Q}",
        {"name": "Pensja", "amount": "8000.00", "day": TODAY.day},
    )
    await _post(
        db_session,
        me,
        f"/api/v1/income/bills{Q}",
        {"name": "Internet", "amount": "60.00", "day": TODAY.day},
    )
    await _bought(me, "140.00")

    views = await _views(db_session, me)
    card = views["accounts"]["accounts"]

    assert [a["name"] for a in card] == ["Moja karta"]
    assert _money(views["balance"]["balance"]) == _money(views["accounts"]["total"])
    assert _money(views["accounts"]["total"]) == Decimal("7800.00")
    assert _money(views["month"]["total"]) == Decimal("8000.00")


def test_the_month_these_tests_write_into_is_open() -> None:
    assert MONTH <= TODAY < MONTH + timedelta(days=31) and isinstance(TODAY, date)


@pytest.mark.asyncio
async def test_a_late_document_lands_in_last_month_on_its_own_date(
    db_session: AsyncSession,
) -> None:
    """A payslip for last month arriving now is added there; that month stays closed."""
    me = await UserFactory.create_async(currency="PLN")
    last_day = MONTH - timedelta(days=1)
    await _post(
        db_session,
        me,
        f"/api/v1/accounts{Q}",
        {
            "name": "Card",
            "opening": "0.00",
            "opening_on": last_day.replace(day=1).isoformat(),
            "for_purchases": True,
        },
    )

    late = await _post(
        db_session,
        me,
        "/api/v1/income",
        {
            "received_on": last_day.isoformat(),
            "amount": "4000.00",
            "source": "Employer",
            "channel": "document",
        },
    )
    last_month = (
        await _call(db_session, me, "GET", f"/api/v1/income?month={last_day:%Y-%m}")
    ).json()
    change = await _call(
        db_session,
        me,
        "PUT",
        f"/api/v1/income/{late['id']}",
        {"received_on": last_day.isoformat(), "amount": "1.00", "source": "Employer"},
    )

    assert _money(last_month["total"]) == Decimal("4000.00")
    assert change.json()["code"] == "month_closed"
