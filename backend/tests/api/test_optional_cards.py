"""Cards when wanted (F23.21): a budget alone counts bills; weekly bills count as often as
they fall."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.receipt import ReceiptStatus
from tests.api.test_household import _call
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

TODAY = datetime.now(UTC).date()
MONTH = TODAY.replace(day=1)


async def _bought(user_id: object, amount: str) -> None:
    receipt = await ReceiptFactory.create_async(
        user_id=user_id,
        transaction_date=datetime.combine(MONTH, datetime.min.time(), UTC),
        total_amount=Decimal(amount),
        status=ReceiptStatus.PARSED,
        file_ids=[],
    )
    await LineItemFactory.create_async(
        receipt=receipt,
        name="Groceries",
        quantity=Decimal(1),
        unit_price=Decimal(amount),
        total_price=Decimal(amount),
        category=None,
    )


def _mondays(first_day: date) -> int:
    return sum(
        1
        for d in range(1, 32)
        if _valid(first_day, d)
        and first_day.replace(day=d).weekday() == 0
        and first_day.replace(day=d) >= TODAY
    )


def _valid(first_day: date, day: int) -> bool:
    try:
        first_day.replace(day=day)
    except ValueError:
        return False
    return True


@pytest.mark.asyncio
async def test_a_budget_alone_counts_bills_and_purchases_against_it_with_no_card(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN", budget_limit=Decimal("2000.00"))
    await _bought(me.id, "300.00")
    internet = await _call(
        db_session,
        me,
        "POST",
        f"/api/v1/income/bills?today={TODAY.isoformat()}",
        {"name": "Internet", "amount": "60.00", "day": 28},
    )

    month = (
        await _call(
            db_session,
            me,
            "GET",
            f"/api/v1/budget/months/{MONTH.year}/{MONTH.month}?today={TODAY.isoformat()}",
        )
    ).json()
    accounts = (await _call(db_session, me, "GET", "/api/v1/accounts")).json()

    assert internet.json()["account_id"] is None
    assert accounts["accounts"] == []
    assert (Decimal(month["total"]), Decimal(month["bills_total"])) == (
        Decimal("300.00"),
        Decimal("60.00"),
    )
    assert Decimal(month["limit_remaining"]) == Decimal("1640.00")


@pytest.mark.asyncio
async def test_a_weekly_bill_counts_each_of_its_days_in_the_month_and_in_spending(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    added = await _call(
        db_session,
        me,
        "POST",
        f"/api/v1/income/bills?today={TODAY.isoformat()}",
        {"name": "Gym", "amount": "50.00", "weekday": 0},
    )
    times = _mondays(MONTH)

    month = (await _call(db_session, me, "GET", f"/api/v1/income?month={MONTH:%Y-%m}")).json()
    spending = (
        await _call(
            db_session,
            me,
            "GET",
            f"/api/v1/statistics/categories?start={MONTH.isoformat()}&end={TODAY.isoformat()}",
        )
    ).json()

    assert added.status_code == 201, added.text
    assert added.json()["weekday"] == 0
    assert Decimal(month["bills_total"]) == Decimal("50.00") * times
    assert Decimal(month["bills"][0]["this_month"]) == Decimal("50.00") * times
    passed = 1 if TODAY.weekday() == 0 else 0
    assert Decimal(spending["bills_total"]) == Decimal("50.00") * passed
