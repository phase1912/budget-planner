"""Money coming in, and the account's appearance and setup (F23.10, F23.1, F23.9, N2)."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db.session import get_db_session
from app.domain.accounts import AccountKind
from app.main import create_app
from app.models.account import Account
from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.api.income_card import on_a_card
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory


async def _call(
    session: AsyncSession, method: str, url: str, *, user: User, json: Any = None
) -> Response:
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
    ) as client:
        return await client.request(method, url, json=on_a_card(method, url, json))


@pytest.mark.asyncio
async def test_the_usual_income_stands_in_until_the_month_has_entries(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    await _call(db_session, "PATCH", "/users/me", user=user, json={"usual_income": "6800.00"})

    empty = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=user)).json()
    assert empty["total"] == "6800.00" and empty["entered"] is False

    added = await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={"received_on": "2026-10-10", "amount": "6200.00", "source": "ACME"},
    )
    assert added.status_code == 201
    await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={"received_on": "2026-11-01", "amount": "100.00", "source": "Next month"},
    )
    october = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=user)).json()
    assert october["total"] == "6200.00" and october["entered"] is True
    assert [e["source"] for e in october["entries"]] == ["ACME"]


@pytest.mark.asyncio
async def test_another_users_income_cannot_be_changed_or_seen(db_session: AsyncSession) -> None:
    ann = await UserFactory.create_async()
    bob = await UserFactory.create_async()
    entry = (
        await _call(
            db_session,
            "POST",
            "/api/v1/income",
            user=ann,
            json={"received_on": "2026-10-10", "amount": "10.00", "source": "Gift"},
        )
    ).json()

    body = {"received_on": "2026-10-10", "amount": "99.00", "source": "Mine now"}
    url = f"/api/v1/income/{entry['id']}"
    assert (await _call(db_session, "PUT", url, user=bob, json=body)).status_code == 404
    assert (await _call(db_session, "DELETE", url, user=bob)).status_code == 404
    bobs = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=bob)).json()
    assert bobs["entries"] == []


@pytest.mark.asyncio
async def test_the_look_and_the_first_sign_in_are_kept_on_the_account(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    me = (await _call(db_session, "GET", "/users/me", user=user)).json()
    assert me["palette"] is None and me["onboarded_at"] is None

    changed = await _call(
        db_session,
        "PATCH",
        "/users/me",
        user=user,
        json={
            "palette": "rose",
            "dark_at_night": True,
            "travels_for_work": True,
            "onboarded": True,
        },
    )
    body = changed.json()
    assert body["palette"] == "rose" and body["dark_at_night"] and body["travels_for_work"]
    assert body["onboarded_at"] is not None

    refused = await _call(db_session, "PATCH", "/users/me", user=user, json={"palette": "neon"})
    assert refused.status_code == 422


@pytest.mark.asyncio
async def test_the_balance_moves_with_income_and_counted_purchases_since_it_was_entered(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    url = "/api/v1/income/balance?today=2026-10-20"
    assert (await _call(db_session, "GET", url, user=user)).json()["balance"] is None

    await _call(
        db_session,
        "PATCH",
        "/users/me",
        user=user,
        json={"starting_balance": "5000.00", "balance_since": "2026-10-01"},
    )
    for day, amount, status in [
        (5, "169.00", ReceiptStatus.PARSED),
        (6, "40.00", ReceiptStatus.MANUAL_REVIEW),  # not counted until resolved (D3)
    ]:
        receipt = await ReceiptFactory.create_async(
            user_id=user.id,
            transaction_date=datetime(2026, 10, day, tzinfo=UTC),
            total_amount=Decimal(amount),
            status=status,
            file_ids=[],
        )
        await LineItemFactory.create_async(
            receipt=receipt,
            name="Thing",
            quantity=Decimal(1),
            unit_price=Decimal(amount),
            total_price=Decimal(amount),
            category=None,
        )
    await ReceiptFactory.create_async(  # before the start: not in the balance
        user_id=user.id,
        transaction_date=datetime(2026, 9, 30, tzinfo=UTC),
        status=ReceiptStatus.PARSED,
        file_ids=[],
    )
    after_purchase = (await _call(db_session, "GET", url, user=user)).json()
    assert after_purchase["balance"] == "4831.00"

    await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={"received_on": "2026-10-10", "amount": "6200.00", "source": "ACME"},
    )
    after_salary = (await _call(db_session, "GET", url, user=user)).json()
    assert after_salary == {
        "balance": "11031.00",
        "since": "2026-10-01",
        "starting": "5000.00",
        "came_in": "6200.00",
        "spent": "169.00",
        # The first income opened the purchase card with the balance as it was started
        # (F23.15): the same figures, now added up from the account.
        "taxes_paid": "0.00",
        "bills": "0.00",
        "for_taxes": "0.00",
        "from_accounts": True,
    }


@pytest.mark.asyncio
async def test_one_who_pays_their_own_taxes_sees_what_is_theirs_to_keep(
    db_session: AsyncSession,
) -> None:
    """F23.16: 20 000 earned is taxed by its kind, a 1 000 gift is not; the fixed sum once."""
    user = await UserFactory.create_async()
    await _call(
        db_session,
        "PATCH",
        "/users/me",
        user=user,
        json={
            "pays_own_taxes": True,
            "tax_rate": "12",
            "tax_fixed_monthly": "1600",
            "starting_balance": "0",
            "balance_since": "2026-10-01",
        },
    )
    entry = {"received_on": "2026-10-05", "source": "x"}
    salary = await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={**entry, "amount": "20000.00", "kind": "side"},
    )
    gift = await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={**entry, "amount": "1000.00", "kind": "other"},
    )
    assert (salary.json()["taxed"], gift.json()["taxed"]) == (True, False)

    month = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=user)).json()
    assert (month["total"], month["taxes"], month["net"]) == ("21000.00", "4000.00", "17000.00")

    paid = await _call(
        db_session,
        "POST",
        "/api/v1/income/taxes",
        user=user,
        json={"paid_on": "2026-10-20", "amount": "1600.00"},
    )
    assert paid.status_code == 201
    balance = (
        await _call(db_session, "GET", "/api/v1/income/balance?today=2026-10-25", user=user)
    ).json()
    assert (balance["balance"], balance["for_taxes"]) == ("19400.00", "2400.00")
    month = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=user)).json()
    assert month["taxes_paid"] == "1600.00"


@pytest.mark.asyncio
async def test_a_gift_marked_taxed_by_hand_stays_so_until_changed(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    entry = {"received_on": "2026-10-05", "source": "x", "amount": "300.00", "kind": "other"}
    made = (
        await _call(db_session, "POST", "/api/v1/income", user=user, json={**entry, "taxed": True})
    ).json()
    kept = (
        await _call(db_session, "PUT", f"/api/v1/income/{made['id']}", user=user, json=entry)
    ).json()
    cleared = (
        await _call(
            db_session,
            "PUT",
            f"/api/v1/income/{made['id']}",
            user=user,
            json={**entry, "taxed": False},
        )
    ).json()

    assert (made["taxed"], kept["taxed"], cleared["taxed"]) == (True, True, False)


@pytest.mark.asyncio
async def test_another_users_tax_payments_are_neither_seen_nor_removed(
    db_session: AsyncSession,
) -> None:
    """N2."""
    owner = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    paid = (
        await _call(
            db_session,
            "POST",
            "/api/v1/income/taxes",
            user=owner,
            json={"paid_on": "2026-10-20", "amount": "100.00"},
        )
    ).json()

    listed = await _call(db_session, "GET", "/api/v1/income/taxes?month=2026-10", user=stranger)
    removed = await _call(db_session, "DELETE", f"/api/v1/income/taxes/{paid['id']}", user=stranger)

    assert listed.json() == []
    assert removed.status_code == 404


@pytest.mark.asyncio
async def test_regular_incomes_count_every_month_and_ending_one_keeps_the_past(
    db_session: AsyncSession,
) -> None:
    """F23.17: a salary and a side income, already net, with 500 more entered on top."""
    user = await UserFactory.create_async()
    base = "/api/v1/income/regular"
    salary = await _call(
        db_session,
        "POST",
        f"{base}?today=2026-10-01",
        user=user,
        json={"name": "Salary", "amount": "10000.00", "day": 10},
    )
    await _call(
        db_session,
        "POST",
        f"{base}?today=2026-10-01",
        user=user,
        json={"name": "Side", "amount": "1000.00"},
    )
    await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={"received_on": "2026-10-15", "amount": "500.00", "source": "Gift", "kind": "other"},
    )

    october = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=user)).json()
    september = (await _call(db_session, "GET", "/api/v1/income?month=2026-09", user=user)).json()
    assert october["total"] == "11500.00"
    assert [r["name"] for r in october["regular"]] == ["Salary", "Side"]
    assert september["regular"] == []

    await _call(db_session, "DELETE", f"{base}/{salary.json()['id']}?today=2026-11-20", user=user)
    november = (await _call(db_session, "GET", "/api/v1/income?month=2026-11", user=user)).json()
    december = (await _call(db_session, "GET", "/api/v1/income?month=2026-12", user=user)).json()
    listed = (await _call(db_session, "GET", base, user=user)).json()
    assert november["total"] == "11000.00"
    assert december["total"] == "1000.00"
    assert [r["name"] for r in listed] == ["Side"]


@pytest.mark.asyncio
async def test_the_balance_gains_the_salary_on_its_day(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    await _call(
        db_session,
        "PATCH",
        "/users/me",
        user=user,
        json={"starting_balance": "100", "balance_since": "2026-10-01"},
    )
    await _call(
        db_session,
        "POST",
        "/api/v1/income/regular?today=2026-10-01",
        user=user,
        json={"name": "Salary", "amount": "10000.00", "day": 10},
    )

    before = await _call(db_session, "GET", "/api/v1/income/balance?today=2026-10-09", user=user)
    after = await _call(db_session, "GET", "/api/v1/income/balance?today=2026-10-10", user=user)

    assert (before.json()["balance"], after.json()["balance"]) == ("100.00", "10100.00")


@pytest.mark.asyncio
async def test_another_users_regular_income_cannot_be_changed_or_ended(
    db_session: AsyncSession,
) -> None:
    """N2."""
    owner = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    made = (
        await _call(
            db_session,
            "POST",
            "/api/v1/income/regular",
            user=owner,
            json={"name": "Salary", "amount": "10000.00"},
        )
    ).json()
    url = f"/api/v1/income/regular/{made['id']}"

    changed = await _call(
        db_session, "PUT", url, user=stranger, json={"name": "Mine", "amount": "1.00"}
    )
    ended = await _call(db_session, "DELETE", url, user=stranger)
    listed = await _call(db_session, "GET", "/api/v1/income/regular", user=stranger)

    assert (changed.status_code, ended.status_code, listed.json()) == (404, 404, [])


@pytest.mark.asyncio
async def test_tax_comes_out_of_a_regular_income_marked_taxed(db_session: AsyncSession) -> None:
    """F23.16 with F23.17: 12 % of the taxed salary plus 1 600, nothing from the pension."""
    user = await UserFactory.create_async()
    await _call(
        db_session,
        "PATCH",
        "/users/me",
        user=user,
        json={
            "pays_own_taxes": True,
            "tax_rate": "12",
            "tax_fixed_monthly": "1600",
            "starting_balance": "0",
            "balance_since": "2026-10-01",
        },
    )
    for body in (
        {"name": "Salary", "amount": "10000.00", "day": 10, "taxed": True},
        {"name": "Pension", "amount": "1000.00", "day": 5},
    ):
        await _call(
            db_session, "POST", "/api/v1/income/regular?today=2026-10-01", user=user, json=body
        )

    month = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=user)).json()
    balance = (
        await _call(db_session, "GET", "/api/v1/income/balance?today=2026-10-20", user=user)
    ).json()

    assert (month["total"], month["taxes"], month["net"]) == ("11000.00", "2800.00", "8200.00")
    assert (balance["balance"], balance["for_taxes"]) == ("11000.00", "2800.00")


@pytest.mark.asyncio
async def test_a_regular_bill_counts_each_month_and_leaves_the_balance_on_its_day(
    db_session: AsyncSession,
) -> None:
    """F23.18: rent of 3 000 on the 5th, from the month it was added."""
    user = await UserFactory.create_async()
    await _call(
        db_session,
        "PATCH",
        "/users/me",
        user=user,
        json={"starting_balance": "5000", "balance_since": "2026-10-01"},
    )
    rent = (
        await _call(
            db_session,
            "POST",
            "/api/v1/income/bills?today=2026-10-01",
            user=user,
            json={"name": "Rent", "amount": "3000.00", "day": 5},
        )
    ).json()

    october = (await _call(db_session, "GET", "/api/v1/income?month=2026-10", user=user)).json()
    september = (await _call(db_session, "GET", "/api/v1/income?month=2026-09", user=user)).json()
    before = await _call(db_session, "GET", "/api/v1/income/balance?today=2026-10-04", user=user)
    after = await _call(db_session, "GET", "/api/v1/income/balance?today=2026-10-05", user=user)

    assert ([b["name"] for b in october["bills"]], october["bills_total"]) == (["Rent"], "3000.00")
    assert september["bills"] == []
    assert (before.json()["balance"], after.json()["balance"]) == ("5000.00", "2000.00")

    await _call(
        db_session, "DELETE", f"/api/v1/income/bills/{rent['id']}?today=2026-11-20", user=user
    )
    november = (await _call(db_session, "GET", "/api/v1/income?month=2026-11", user=user)).json()
    december = (await _call(db_session, "GET", "/api/v1/income?month=2026-12", user=user)).json()
    assert (november["bills_total"], december["bills_total"]) == ("3000.00", "0.00")


@pytest.mark.asyncio
async def test_another_users_bill_cannot_be_seen_changed_or_stopped(
    db_session: AsyncSession,
) -> None:
    """N2."""
    owner = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    rent = (
        await _call(
            db_session,
            "POST",
            "/api/v1/income/bills",
            user=owner,
            json={"name": "Rent", "amount": "3000.00"},
        )
    ).json()
    url = f"/api/v1/income/bills/{rent['id']}"

    listed = await _call(db_session, "GET", "/api/v1/income/bills", user=stranger)
    changed = await _call(db_session, "PUT", url, user=stranger, json={"name": "x", "amount": "1"})
    ended = await _call(db_session, "DELETE", url, user=stranger)

    assert (listed.json(), changed.status_code, ended.status_code) == ([], 404, 404)


@pytest.mark.asyncio
async def test_income_and_bills_associated_with_account(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    account = Account(
        user_id=user.id,
        name="Business",
        kind=AccountKind.BUSINESS,
        opening=Decimal("1000.00"),
        opening_on=datetime(2026, 10, 1, tzinfo=UTC).date(),
        tax_rate=Decimal("10.00"),
    )
    db_session.add(account)
    await db_session.flush()

    reg = await _call(
        db_session,
        "POST",
        "/api/v1/income/regular?today=2026-10-01",
        user=user,
        json={"name": "Consulting", "amount": "4000.00", "day": 10, "account_id": str(account.id)},
    )
    assert reg.status_code == 201
    assert reg.json()["account_id"] == str(account.id)

    ch_reg = await _call(
        db_session,
        "PUT",
        f"/api/v1/income/regular/{reg.json()['id']}?today=2026-10-02",
        user=user,
        json={
            "name": "Consulting Plus",
            "amount": "4500.00",
            "day": 12,
            "account_id": str(account.id),
        },
    )
    assert ch_reg.status_code == 200

    bill = await _call(
        db_session,
        "POST",
        "/api/v1/income/bills?today=2026-10-01",
        user=user,
        json={"name": "Server", "amount": "100.00", "day": 5, "account_id": str(account.id)},
    )
    assert bill.status_code == 201
    assert bill.json()["account_id"] == str(account.id)

    ch_bill = await _call(
        db_session,
        "PUT",
        f"/api/v1/income/bills/{bill.json()['id']}",
        user=user,
        json={
            "name": "Cloud Server",
            "amount": "120.00",
            "day": 5,
            "account_id": str(account.id),
        },
    )
    assert ch_bill.status_code == 200

    inc = await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={
            "received_on": "2026-10-05",
            "amount": "2000.00",
            "source": "Client A",
            "account_id": str(account.id),
        },
    )
    assert inc.status_code == 201

    ch_inc = await _call(
        db_session,
        "PUT",
        f"/api/v1/income/{inc.json()['id']}",
        user=user,
        json={
            "received_on": "2026-10-06",
            "amount": "2500.00",
            "source": "Client A+",
            "account_id": str(account.id),
        },
    )
    assert ch_inc.status_code == 200

    tax_res = await _call(
        db_session,
        "POST",
        "/api/v1/income/taxes",
        user=user,
        json={"paid_on": "2026-10-07", "amount": "250.00", "account_id": str(account.id)},
    )
    assert tax_res.status_code == 201

    bal_res = await _call(db_session, "GET", "/api/v1/income/balance?today=2026-10-15", user=user)
    assert bal_res.status_code == 200
    bal_data = bal_res.json()
    assert bal_data["from_accounts"] is True

    del_inc = await _call(db_session, "DELETE", f"/api/v1/income/{inc.json()['id']}", user=user)
    assert del_inc.status_code == 204

    missing_id = str(uuid.uuid4())
    bad_acc = await _call(
        db_session,
        "POST",
        "/api/v1/income",
        user=user,
        json={
            "received_on": "2026-10-05",
            "amount": "100.00",
            "source": "X",
            "account_id": missing_id,
        },
    )
    assert bad_acc.status_code == 404
