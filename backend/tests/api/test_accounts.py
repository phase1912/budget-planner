"""Accounts and the money between them (F23.15, N2)."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import RegularTransfer
from app.models.household import HouseholdRole
from app.models.receipt import ReceiptStatus
from app.models.tax_payment import TaxPayment
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
async def test_a_closed_month_takes_a_late_entry_but_keeps_what_it_holds(
    db_session: AsyncSession,
) -> None:
    """F23.15: a late document is added on its own date; a closed month's entries stay."""
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
    october = await _history(db_session, me, card["id"], 2, month="2026-10")
    move_id = october["entries"][0]["ref_id"]
    changed = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/moves/{move_id}?today=2026-11-02",
        {"amount": "1.00", "moved_on": "2026-10-30"},
    )
    removed = await _call(db_session, me, "DELETE", f"{URL}/moves/{move_id}?today=2026-11-02")

    assert back_dated.status_code == 201
    assert (changed.status_code, changed.json()["code"]) == (409, "month_closed")
    assert removed.json()["code"] == "month_closed"


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


@pytest.mark.asyncio
async def test_change_account_and_delete_account(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    card = await _open(db_session, me, name="Main card", opening="100.00")

    changed = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/{card['id']}{on(1)}",
        {
            "name": "Family card",
            "kind": "personal",
            "opening": "200.00",
            "opening_on": "2026-10-01",
            "shared": True,
            "for_purchases": True,
        },
    )
    assert changed.status_code == 200, changed.text
    data = changed.json()
    assert data["name"] == "Family card"
    assert data["shared"] is True
    assert Decimal(data["balance"]) == Decimal("200.00")

    anna_accounts = await _accounts(db_session, anna, 1)
    assert "Family card" in anna_accounts

    missing_id = str(uuid.uuid4())
    res_404 = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/{missing_id}{on(1)}",
        {"name": "X", "kind": "personal", "opening": "0.00"},
    )
    assert res_404.status_code == 404

    deleted = await _call(db_session, me, "DELETE", f"{URL}/{card['id']}")
    assert deleted.status_code == 204
    after_delete = await _accounts(db_session, me, 1)
    assert "Family card" not in after_delete


@pytest.mark.asyncio
async def test_only_purchase_card_unmarks_previous(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    await _open(db_session, me, name="Card 1", for_purchases=True)
    await _open(db_session, me, name="Card 2", for_purchases=True)

    accs = await _accounts(db_session, me, 1)
    assert accs["Card 1"]["for_purchases"] is False
    assert accs["Card 2"]["for_purchases"] is True


@pytest.mark.asyncio
async def test_cannot_share_account_without_household(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    res = await _call(
        db_session,
        me,
        "POST",
        f"{URL}{on(1)}",
        {"name": "Shared", "kind": "personal", "opening": "0.00", "shared": True},
    )
    assert res.status_code == 409
    assert res.json()["code"] == "not_in_household"


@pytest.mark.asyncio
async def test_money_in_transfer_and_change_income(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    biz = await _open(db_session, me, name="Biz", kind="business", tax_rate="10")
    card = await _open(db_session, me, name="Card", opening="500.00")

    t_res = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/{card['id']}/money-in{on(5)}",
        {
            "amount": "200.00",
            "source": "Transfer",
            "received_on": "2026-10-05",
            "from_account_id": biz["id"],
        },
    )
    assert t_res.status_code == 201

    inc_res = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/{biz['id']}/money-in{on(5)}",
        {"amount": "1000.00", "source": "Client", "received_on": "2026-10-05"},
    )
    assert inc_res.status_code == 201

    biz_history = await _history(db_session, me, biz["id"], 5)
    income_entry = next(e for e in biz_history["entries"] if e["kind"] == "income")
    income_id = income_entry["ref_id"]

    changed = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/incomes/{income_id}{on(6)}",
        {"amount": "1200.00", "received_on": "2026-10-06"},
    )
    assert changed.status_code == 204

    updated_history = await _history(db_session, me, biz["id"], 6)
    updated_income = next(e for e in updated_history["entries"] if e["kind"] == "income")
    assert Decimal(updated_income["amount"]) == Decimal("1200.00")
    assert Decimal(updated_income["tax"]) == Decimal("120.00")

    missing_id = str(uuid.uuid4())
    res_404 = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/incomes/{missing_id}{on(6)}",
        {"amount": "500.00", "received_on": "2026-10-06"},
    )
    assert res_404.status_code == 404

    res_closed = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/incomes/{income_id}?today=2026-11-01",
        {"amount": "1500.00", "received_on": "2026-10-06"},
    )
    assert res_closed.status_code == 409
    assert res_closed.json()["code"] == "month_closed"


@pytest.mark.asyncio
async def test_change_move_and_delete_move(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    acc1 = await _open(db_session, me, name="Acc1", opening="500.00")
    acc2 = await _open(db_session, me, name="Acc2", opening="0.00")

    move_res = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/moves{on(5)}",
        {
            "from_account_id": acc1["id"],
            "to_account_id": acc2["id"],
            "amount": "100.00",
            "moved_on": "2026-10-05",
        },
    )
    assert move_res.status_code == 201

    history = await _history(db_session, me, acc1["id"], 5)
    move_entry = next(e for e in history["entries"] if e["kind"] == "transfer_out")
    move_id = move_entry["ref_id"]

    ch_res = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/moves/{move_id}{on(6)}",
        {"amount": "150.00", "moved_on": "2026-10-06"},
    )
    assert ch_res.status_code == 204

    accs = await _accounts(db_session, me, 6)
    assert Decimal(accs["Acc1"]["balance"]) == Decimal("350.00")
    assert Decimal(accs["Acc2"]["balance"]) == Decimal("150.00")

    missing_id = str(uuid.uuid4())
    res_404 = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/moves/{missing_id}{on(6)}",
        {"amount": "50.00", "moved_on": "2026-10-06"},
    )
    assert res_404.status_code == 404

    del_res = await _call(db_session, me, "DELETE", f"{URL}/moves/{move_id}{on(6)}")
    assert del_res.status_code == 204
    accs_after = await _accounts(db_session, me, 6)
    assert Decimal(accs_after["Acc1"]["balance"]) == Decimal("500.00")

    del_404 = await _call(db_session, me, "DELETE", f"{URL}/moves/{missing_id}{on(6)}")
    assert del_404.status_code == 404


@pytest.mark.asyncio
async def test_same_account_transfers_and_moves_refused(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    acc = await _open(db_session, me, name="Acc", opening="500.00")

    res_move = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/moves{on(1)}",
        {
            "from_account_id": acc["id"],
            "to_account_id": acc["id"],
            "amount": "50.00",
            "moved_on": "2026-10-01",
        },
    )
    assert res_move.status_code == 409
    assert res_move.json()["code"] == "same_account"

    res_transfer = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/transfers{on(1)}",
        {
            "from_account_id": acc["id"],
            "to_account_id": acc["id"],
            "amount": "50.00",
            "day": 10,
        },
    )
    assert res_transfer.status_code == 409
    assert res_transfer.json()["code"] == "same_account"


@pytest.mark.asyncio
async def test_adjust_account_balance_positive_and_negative(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    acc = await _open(db_session, me, name="Bank", opening="500.00")

    pos_res = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/{acc['id']}/adjust{on(5)}",
        {"balance": "600.00"},
    )
    assert pos_res.status_code == 201
    accs = await _accounts(db_session, me, 5)
    assert Decimal(accs["Bank"]["balance"]) == Decimal("600.00")

    neg_res = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/{acc['id']}/adjust{on(6)}",
        {"balance": "450.00"},
    )
    assert neg_res.status_code == 201
    accs2 = await _accounts(db_session, me, 6)
    assert Decimal(accs2["Bank"]["balance"]) == Decimal("450.00")

    missing_id = str(uuid.uuid4())
    res_404 = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/{missing_id}/adjust{on(6)}",
        {"balance": "500.00"},
    )
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_transfer_rules_crud(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    src = await _open(db_session, me, name="Checking", opening="1000.00")
    dst = await _open(db_session, me, name="Savings", opening="0.00")

    rule_res = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/transfers{on(2)}",
        {
            "from_account_id": src["id"],
            "to_account_id": dst["id"],
            "amount": "200.00",
            "day": 10,
            "name": "Save 200",
        },
    )
    assert rule_res.status_code == 201
    rule_id = rule_res.json()["id"]

    rules_list = (await _call(db_session, me, "GET", f"{URL}/transfers")).json()
    assert len(rules_list) == 1
    assert rules_list[0]["name"] == "Save 200"

    ch_res = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/transfers/{rule_id}",
        {
            "from_account_id": src["id"],
            "to_account_id": dst["id"],
            "amount": "250.00",
            "day": 15,
            "name": "Save 250",
        },
    )
    assert ch_res.status_code == 200
    assert ch_res.json()["amount"] == "250.00"

    missing_id = str(uuid.uuid4())
    res_404 = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/transfers/{missing_id}",
        {
            "from_account_id": src["id"],
            "to_account_id": dst["id"],
            "amount": "250.00",
            "day": 15,
        },
    )
    assert res_404.status_code == 404

    end_res = await _call(db_session, me, "DELETE", f"{URL}/transfers/{rule_id}{on(16)}")
    assert end_res.status_code == 204
    rules_after = (await _call(db_session, me, "GET", f"{URL}/transfers")).json()
    assert rules_after == []

    past_rule = RegularTransfer(
        user_id=me.id,
        name="Past",
        amount=Decimal("100.00"),
        day=5,
        starts_on=date(2026, 9, 1),
        from_account_id=uuid.UUID(src["id"]),
        to_account_id=uuid.UUID(dst["id"]),
    )
    db_session.add(past_rule)
    await db_session.flush()

    end_past = await _call(db_session, me, "DELETE", f"{URL}/transfers/{past_rule.id}{on(16)}")
    assert end_past.status_code == 204
    rules_after_past = (await _call(db_session, me, "GET", f"{URL}/transfers")).json()
    assert rules_after_past == []


@pytest.mark.asyncio
async def test_occurrence_for_transfer_and_bill_edge_cases(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    card = await _open(db_session, me, name="Card", opening="1000.00")
    dst = await _open(db_session, me, name="Savings", opening="0.00")

    rule_res = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/transfers{on(1)}",
        {
            "from_account_id": card["id"],
            "to_account_id": dst["id"],
            "amount": "100.00",
            "day": 10,
        },
    )
    rule_id = rule_res.json()["id"]

    occ_res = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/occurrences/{rule_id}{on(5)}",
        {"kind": "transfer", "amount": "120.00"},
    )
    assert occ_res.status_code == 204

    missing_id = str(uuid.uuid4())
    res_404 = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/occurrences/{missing_id}{on(5)}",
        {"kind": "transfer", "amount": "50.00"},
    )
    assert res_404.status_code == 404

    bill_no_acc = await _call(
        db_session,
        me,
        "POST",
        f"/api/v1/income/bills{on(1)}",
        {"name": "No Acc Bill", "amount": "50.00", "day": 5},
    )
    bill_no_acc_id = bill_no_acc.json()["id"]
    # A bill named on no account goes on the purchase card, so its month can be changed.
    assert bill_no_acc.json()["account_id"] == card["id"]
    changed = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/occurrences/{bill_no_acc_id}{on(5)}",
        {"kind": "bill", "amount": "60.00"},
    )
    assert changed.status_code == 204

    bill_404 = await _call(
        db_session,
        me,
        "PUT",
        f"{URL}/occurrences/{missing_id}{on(5)}",
        {"kind": "bill", "amount": "60.00"},
    )
    assert bill_404.status_code == 404


@pytest.mark.asyncio
async def test_tax_payment_and_private_receipt_entries(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    card = await _open(db_session, me, name="Our card", opening="2000.00", shared=True)

    tax_payment = TaxPayment(
        user_id=me.id,
        account_id=uuid.UUID(card["id"]),
        paid_on=date(2026, 10, 5),
        amount=Decimal("300.00"),
    )
    db_session.add(tax_payment)
    await db_session.flush()

    receipt = await ReceiptFactory.create_async(
        user_id=anna.id,
        transaction_date=datetime(2026, 10, 6, tzinfo=UTC),
        total_amount=Decimal("80.00"),
        status=ReceiptStatus.PARSED,
        file_ids=[],
        is_private=True,
    )
    await LineItemFactory.create_async(
        receipt=receipt,
        name="Private item",
        quantity=Decimal(1),
        unit_price=Decimal("80.00"),
        total_price=Decimal("80.00"),
    )

    history = await _history(db_session, me, card["id"], 10)
    entries = history["entries"]
    kinds = [e["kind"] for e in entries]
    assert "tax_paid" in kinds
    tax_entry = next(e for e in entries if e["kind"] == "tax_paid")
    assert Decimal(tax_entry["amount"]) == Decimal("-300.00")

    private_entry = next(e for e in entries if e["author"] == "private")
    assert Decimal(private_entry["amount"]) == Decimal("-80.00")


@pytest.mark.asyncio
async def test_child_cannot_modify_or_delete_shared_account(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(first_name="Bohdan", currency="PLN")
    child = await UserFactory.create_async(first_name="Child", currency="PLN")
    household = await HouseholdFactory.create_async()
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=me.id, role=HouseholdRole.OWNER.value
    )
    await HouseholdMemberFactory.create_async(
        household_id=household.id, user_id=child.id, role=HouseholdRole.CHILD.value
    )
    card = await _open(db_session, me, name="Shared card", opening="1000.00", shared=True)

    mod_res = await _call(
        db_session,
        child,
        "PUT",
        f"{URL}/{card['id']}{on(1)}",
        {"name": "Hacked", "kind": "personal", "opening": "0.00"},
    )
    assert mod_res.status_code == 403
    assert mod_res.json()["code"] == "child_read_only"

    del_res = await _call(db_session, child, "DELETE", f"{URL}/{card['id']}")
    assert del_res.status_code == 403
    assert del_res.json()["code"] == "child_read_only"


@pytest.mark.asyncio
async def test_expected_income_and_confirm_edge_cases(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    empty_exp = (await _call(db_session, me, "GET", f"{URL}/expected{on(1)}")).json()
    assert empty_exp == []

    missing_id = str(uuid.uuid4())
    res_404 = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/expected/{missing_id}/confirm{on(1)}",
        {"amount": "100.00"},
    )
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_regular_income_sources_in_ledger(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    card = await _open(db_session, me, name="Card", opening="0.00", for_purchases=True)

    await _call(
        db_session,
        me,
        "POST",
        f"/api/v1/income/regular{on(1)}",
        {
            "name": "Salary",
            "amount": "5000.00",
            "day": 10,
            "about": False,
            "account_id": card["id"],
        },
    )
    hist_day5 = await _history(db_session, me, card["id"], 5)
    sal5 = next(e for e in hist_day5["entries"] if e["name"] == "Salary")
    assert sal5["upcoming"] is True

    hist_day15 = await _history(db_session, me, card["id"], 15)
    sal15 = next(e for e in hist_day15["entries"] if e["name"] == "Salary")
    assert sal15["upcoming"] is False


@pytest.mark.asyncio
async def test_an_income_named_on_no_account_goes_on_the_purchase_card(
    db_session: AsyncSession,
) -> None:
    """F23.15: once there are accounts, every income is on one — the card by default."""
    me = await UserFactory.create_async(currency="PLN")
    card = await _open(db_session, me, name="Card", opening="0.00")

    income = await _call(
        db_session,
        me,
        "POST",
        "/api/v1/income",
        # Today's: an earlier month is closed once there are accounts.
        {"received_on": datetime.now(UTC).date().isoformat(), "amount": "500.00", "source": "Gift"},
    )
    regular = await _call(
        db_session,
        me,
        "POST",
        f"/api/v1/income/regular{on(1)}",
        {"name": "Salary", "amount": "9000.00", "day": 10},
    )

    assert income.json()["account_id"] == card["id"]
    assert regular.json()["account_id"] == card["id"]


@pytest.mark.asyncio
async def test_the_first_income_opens_the_card_with_the_balance_kept_so_far(
    db_session: AsyncSession,
) -> None:
    """F23.15: someone without accounts is never asked to make one; the first sum opens it."""
    me = await UserFactory.create_async(
        currency="PLN",
        language="uk",
        starting_balance=Decimal("5000.00"),
        balance_since=date(2026, 10, 1),
    )
    today = datetime.now(UTC).date().isoformat()

    added = await _call(
        db_session,
        me,
        "POST",
        "/api/v1/income",
        {"received_on": today, "amount": "100.00", "source": "Gift", "kind": "other"},
    )
    accounts = await _accounts(db_session, me, 20)

    assert added.status_code == 201, added.text
    card = accounts["Моя картка"]
    assert (card["for_purchases"], card["opening"], card["opening_on"]) == (
        True,
        "5000.00",
        "2026-10-01",
    )


@pytest.mark.asyncio
async def test_a_shared_income_with_no_card_opens_the_familys(db_session: AsyncSession) -> None:
    me, anna = await _couple()
    today = datetime.now(UTC).date().isoformat()

    await _call(
        db_session,
        me,
        "POST",
        "/api/v1/income",
        {"received_on": today, "amount": "9000.00", "source": "Acme", "shared": True},
    )
    hers = await _accounts(db_session, anna, 20)

    assert hers["Our card"]["shared"] is True


@pytest.mark.asyncio
async def test_ones_own_tax_rule_holds_on_a_card_without_a_rate(db_session: AsyncSession) -> None:
    """F23.16 with F23.15: a card has no rate, so the user's own rule sets tax aside."""
    me = await UserFactory.create_async(
        currency="PLN",
        pays_own_taxes=True,
        tax_rate=Decimal("12.00"),
        tax_fixed_monthly=Decimal("0.00"),
    )
    await _open(db_session, me, name="Card", opening="0.00", for_purchases=True)

    await _call(
        db_session,
        me,
        "POST",
        "/api/v1/income",
        {
            "received_on": datetime.now(UTC).date().isoformat(),
            "amount": "10000.00",
            "source": "Client",
            "kind": "side",
        },
    )
    month = (
        await _call(db_session, me, "GET", f"/api/v1/income?month={datetime.now(UTC):%Y-%m}")
    ).json()
    balance = (
        await _call(
            db_session,
            me,
            "GET",
            f"/api/v1/income/balance?today={datetime.now(UTC).date().isoformat()}",
        )
    ).json()

    assert Decimal(month["taxes"]) == Decimal("1200.00")
    assert Decimal(balance["for_taxes"]) == Decimal("1200.00")
