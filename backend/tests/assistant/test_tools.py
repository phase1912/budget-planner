"""Everything in words, approved on a card (F21.7): each thing the user keeps can be added,
changed and removed through the assistant — found by the name the user gave it, never
another user's (N2) — and settings and the account have no tool."""

import ast
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.core.ports import ToolCall
from app.assistant.tools import all_tools, card_writers
from app.assistant.tools.base import find_by_name
from app.models.user import User
from tests.assistant.test_api import URL, ScriptedAssistant, _call, _say
from tests.factories.user import UserFactory

TODAY = "2026-10-20"


async def _propose(session: AsyncSession, user: User, *calls: ToolCall) -> list[dict[str, Any]]:
    """The cards the assistant proposes for `calls`, as the conversation holds them."""
    conversation = await _say(session, user, "please", ScriptedAssistant(proposals=calls))
    return [m for m in conversation["messages"] if m["card_state"] == "proposed"]


async def _approve(session: AsyncSession, user: User, card: dict[str, Any]) -> dict[str, Any]:
    saved = await _call(
        session,
        user,
        "POST",
        f"{URL}/cards/{card['id']}/save",
        {"fields": card["card"]["fields"], "today": TODAY},
    )
    assert saved.status_code == 200, saved.text
    return dict(saved.json())


async def _get(session: AsyncSession, user: User, url: str) -> Any:
    return (await _call(session, user, "GET", url)).json()


@pytest.mark.asyncio
async def test_a_bill_is_added_weekly_changed_by_its_name_and_stopped(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    [added] = await _propose(
        db_session, me, ToolCall("add_bill", {"name": "Gym", "amount": "50", "weekday": 0})
    )
    await _approve(db_session, me, added)

    [change] = await _propose(
        db_session, me, ToolCall("change_bill", {"name": "gym", "amount": "60"})
    )
    await _approve(db_session, me, change)
    bills = await _get(db_session, me, "/api/v1/income/bills")
    [stop] = await _propose(db_session, me, ToolCall("stop_bill", {"name": "Gym"}))
    await _approve(db_session, me, stop)

    assert change["card"]["kind"] == "bill_change"
    assert change["card"]["fields"]["target"] == "Gym"
    assert [f["name"] for f in change["card"]["form"]] == ["target", "name", "amount", "repeat"]
    assert [(b["name"], b["amount"], b["weekday"]) for b in bills] == [("Gym", "60.00", 0)]
    assert await _get(db_session, me, "/api/v1/income/bills") == []


@pytest.mark.asyncio
async def test_a_regular_income_makes_its_card_and_is_changed_and_stopped(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN", language="en")
    [added] = await _propose(
        db_session,
        me,
        ToolCall("add_regular_income", {"name": "Salary", "amount": "9000", "day": 28}),
    )
    await _approve(db_session, me, added)
    [change] = await _propose(
        db_session, me, ToolCall("change_regular_income", {"name": "salary", "amount": "9500"})
    )
    await _approve(db_session, me, change)
    regular = await _get(db_session, me, "/api/v1/income/regular")
    [stop] = await _propose(db_session, me, ToolCall("stop_regular_income", {"name": "Salary"}))
    await _approve(db_session, me, stop)
    accounts = await _get(db_session, me, "/api/v1/accounts")

    assert [(r["name"], Decimal(r["amount"])) for r in regular] == [("Salary", Decimal("9500"))]
    assert await _get(db_session, me, "/api/v1/income/regular") == []
    assert [a["name"] for a in accounts["accounts"]] == ["My card"]


@pytest.mark.asyncio
async def test_a_budget_is_removed_and_an_income_taken_out(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN", budget_limit=Decimal("2000.00"))
    [income] = await _propose(
        db_session, me, ToolCall("add_income", {"amount": "100", "source": "Gift"})
    )
    await _approve(db_session, me, income)

    cards = await _propose(
        db_session,
        me,
        ToolCall("remove_budget", {}),
        ToolCall("remove_income", {"source": "gift"}),
    )
    for card in cards:
        await _approve(db_session, me, card)
    await db_session.refresh(me)
    month = await _get(db_session, me, f"/api/v1/income?month={TODAY[:7]}")

    assert [c["card"]["kind"] for c in cards] == ["budget_remove", "income_remove"]
    assert me.budget_limit is None
    assert month["entries"] == []


@pytest.mark.asyncio
async def test_a_goal_is_set_renamed_and_dropped(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    [goal] = await _propose(
        db_session,
        me,
        ToolCall("add_goal", {"name": "Holiday", "kind": "savings_target", "amount": "3000"}),
    )
    await _approve(db_session, me, goal)
    [change] = await _propose(
        db_session, me, ToolCall("change_goal", {"name": "holiday", "amount": "3500"})
    )
    await _approve(db_session, me, change)
    goals = await _get(db_session, me, "/api/v1/goals")
    [drop] = await _propose(db_session, me, ToolCall("remove_goal", {"name": "Holiday"}))
    await _approve(db_session, me, drop)

    assert [(g["name"], Decimal(g["target_amount"])) for g in goals] == [
        ("Holiday", Decimal("3500"))
    ]
    assert await _get(db_session, me, "/api/v1/goals") == []


@pytest.mark.asyncio
async def test_accounts_and_a_monthly_transfer_between_them(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(currency="PLN")
    for name in ("Card", "Savings"):
        [card] = await _propose(
            db_session, me, ToolCall("add_account", {"name": name, "balance": "100"})
        )
        await _approve(db_session, me, card)
    [transfer] = await _propose(
        db_session,
        me,
        ToolCall(
            "add_transfer",
            {"from_account": "card", "to_account": "savings", "amount": "50", "day": 28},
        ),
    )
    await _approve(db_session, me, transfer)
    rules = await _get(db_session, me, "/api/v1/accounts/transfers")
    [stop] = await _propose(db_session, me, ToolCall("stop_transfer", {"name": rules[0]["name"]}))
    await _approve(db_session, me, stop)
    [removal] = await _propose(db_session, me, ToolCall("remove_account", {"name": "Savings"}))
    await _approve(db_session, me, removal)
    accounts = await _get(db_session, me, "/api/v1/accounts")

    assert len(rules) == 1
    assert await _get(db_session, me, "/api/v1/accounts/transfers") == []
    assert [a["name"] for a in accounts["accounts"]] == ["Card"]


@pytest.mark.asyncio
async def test_nothing_is_proposed_for_a_name_the_user_has_none_of_nor_another_users(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    other = await UserFactory.create_async(currency="PLN")
    [theirs] = await _propose(
        db_session, other, ToolCall("add_bill", {"name": "Netflix", "amount": "45"})
    )
    await _approve(db_session, other, theirs)

    cards = await _propose(
        db_session,
        me,
        ToolCall("stop_bill", {"name": "Netflix"}),
        ToolCall("change_goal", {"name": "Car", "amount": "1"}),
    )

    assert cards == []
    assert [b["name"] for b in await _get(db_session, other, "/api/v1/income/bills")] == ["Netflix"]


def test_a_name_is_found_the_way_people_say_it_and_never_guessed_between_two() -> None:
    bills = ["Rent", "Gym", "Gym for kids", "Internet"]

    assert find_by_name(bills, "rent", str).item == "Rent"
    assert find_by_name(bills, "internt", str).item == "Internet"
    assert find_by_name(bills, "gym", str).item == "Gym"
    ambiguous = find_by_name(["Gym A", "Gym B"], "gym", str)
    assert ambiguous.item is None and "Gym A, Gym B" in (ambiguous.error or "")


def test_settings_and_the_account_have_no_tool_and_every_writer_draws_or_owns_a_card() -> None:
    names = set(all_tools())
    for forbidden in ("password", "email", "delete_user", "language", "currency", "settings"):
        assert not any(forbidden in name for name in names)
    own_cards = {"budget", "income", "bill", "expense"}
    for kind, writer in card_writers().items():
        assert kind in own_cards or writer.form, f"{kind} has no form to draw it"


def test_the_core_knows_neither_the_database_nor_http() -> None:
    """ADR-0028: the graph stays a module of its own, testable without the app around it."""
    core = Path(__file__).resolve().parents[2] / "app" / "assistant" / "core"
    banned = ("sqlalchemy", "fastapi", "app.models", "app.repository", "app.services", "app.db")
    for source in core.glob("*.py"):
        for node in ast.walk(ast.parse(source.read_text())):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            for name in names:
                assert not name.startswith(banned), f"{source.name} imports {name}"
