"""A card's balance in words (F21.10): set right to what the bank says — only corrected, or
the difference recorded as purchases never entered — money put on or taken off once, moved
between cards; and the assistant sees everything the user has, never another user's (N2)."""

import json
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.core.ports import ToolCall
from app.models.user import User
from tests.assistant.test_api import ScriptedAssistant, _say
from tests.assistant.test_tools import _approve, _get, _propose
from tests.factories.user import UserFactory


async def _open(session: AsyncSession, user: User, name: str, balance: str, **more: Any) -> None:
    [card] = await _propose(
        session, user, ToolCall("add_account", {"name": name, "balance": balance, **more})
    )
    await _approve(session, user, card)


async def _balances(session: AsyncSession, user: User) -> dict[str, Decimal]:
    accounts = await _get(session, user, "/api/v1/accounts")
    return {a["name"]: Decimal(a["balance"]) for a in accounts["accounts"]}


@pytest.mark.asyncio
async def test_a_lower_bank_balance_is_asked_about_before_any_card(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    await _open(db_session, me, "Revolut", "4100")

    cards = await _propose(
        db_session, me, ToolCall("sync_balance", {"account": "revolut", "balance": "3700"})
    )

    assert cards == []


@pytest.mark.asyncio
async def test_the_difference_recorded_as_purchases_lowers_the_card_and_counts_in_the_month(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN", language="en")
    await _open(db_session, me, "Revolut", "4100")

    [card] = await _propose(
        db_session,
        me,
        ToolCall("sync_balance", {"account": "revolut", "balance": "3700", "way": "spending"}),
    )
    saved = await _approve(db_session, me, card)

    assert card["card"]["kind"] == "balance"
    assert card["card"]["fields"]["target"] == "Revolut: 4100.00 → 3700.00 PLN"
    assert [f["name"] for f in card["card"]["form"]] == [
        "target", "bank_balance", "way", "category_id", "description",
    ]  # fmt: skip
    assert saved["saved_ref"].startswith("receipt:")
    assert await _balances(db_session, me) == {"Revolut": Decimal("3700.00")}
    month = await _get(db_session, me, "/api/v1/budget/months/2026/10")
    assert (Decimal(month["total"]), month["receipt_count"]) == (Decimal("400.00"), 1)


@pytest.mark.asyncio
async def test_a_correction_only_moves_the_balance_and_records_no_purchase(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    await _open(db_session, me, "Revolut", "4100")

    [card] = await _propose(
        db_session,
        me,
        ToolCall("sync_balance", {"account": "revolut", "balance": "3700", "way": "correct"}),
    )
    await _approve(db_session, me, card)

    assert await _balances(db_session, me) == {"Revolut": Decimal("3700.00")}
    month = await _get(db_session, me, "/api/v1/budget/months/2026/10")
    assert month["receipt_count"] == 0


@pytest.mark.asyncio
async def test_no_purchases_on_a_card_not_paid_from_nor_when_the_bank_shows_more(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    await _open(db_session, me, "Card", "1000")
    await _open(db_session, me, "Savings", "5000", kind="deposit")

    cards = await _propose(
        db_session,
        me,
        ToolCall("sync_balance", {"account": "savings", "balance": "4000", "way": "spending"}),
        ToolCall("sync_balance", {"account": "card", "balance": "1200", "way": "spending"}),
    )
    [higher] = await _propose(
        db_session, me, ToolCall("sync_balance", {"account": "card", "balance": "1200"})
    )

    assert cards == []
    assert higher["card"]["fields"]["way"] == "correct"


@pytest.mark.asyncio
async def test_money_put_on_taken_off_and_moved_once(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    await _open(db_session, me, "Card", "1000")
    await _open(db_session, me, "Savings", "0", kind="deposit")

    cards = await _propose(
        db_session,
        me,
        ToolCall("add_money", {"account": "card", "amount": "300", "source": "Gift"}),
        ToolCall("take_money", {"account": "card", "amount": "100", "way": "correct"}),
        ToolCall("move_money", {"from_account": "card", "to_account": "savings", "amount": "500"}),
    )
    for card in cards:
        await _approve(db_session, me, card)

    assert [c["card"]["kind"] for c in cards] == ["money_in", "money_out", "move"]
    assert await _balances(db_session, me) == {
        "Card": Decimal("700.00"),
        "Savings": Decimal("500.00"),
    }


@pytest.mark.asyncio
async def test_another_users_card_is_never_found(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    other = await UserFactory.create_async(currency="PLN")
    await _open(db_session, other, "Theirs", "900")

    cards = await _propose(
        db_session,
        me,
        ToolCall("sync_balance", {"account": "theirs", "balance": "1", "way": "correct"}),
        ToolCall("add_money", {"account": "theirs", "amount": "5", "source": "x"}),
    )

    assert cards == []
    assert await _balances(db_session, other) == {"Theirs": Decimal("900.00")}


@pytest.mark.asyncio
async def test_the_overview_tells_the_user_everything_of_theirs_and_nothing_of_anyone_else(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN", budget_limit=Decimal("2500.00"))
    other = await UserFactory.create_async(currency="PLN")
    await _open(db_session, me, "Mine", "100")
    await _open(db_session, other, "Theirs", "900")
    assistant = ScriptedAssistant(reads=[ToolCall("overview", {})])

    conversation = await _say(db_session, me, "what do you know about me?", assistant)

    figures = json.loads(assistant.read_results[0])
    assert figures["settings"]["monthly_budget"] == "2500.00"
    assert [a["name"] for a in figures["accounts"]["accounts"]] == ["Mine"]
    assert figures["receipt_reads"]["limit"] == 10
    assert "Theirs" not in assistant.read_results[0]
    [answer] = [m for m in conversation["messages"] if m["card"] and m["card"]["kind"] == "answer"]
    assert answer["card"]["fields"]["screen"] == "home"
