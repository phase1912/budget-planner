"""Talking to the assistant, against a real database and a scripted model (F21.1, F21.7, N2)."""

import json
import uuid
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.errors import DomainError
from app.assistant.api import get_assistant
from app.assistant.core.ports import (
    AssistantContext,
    AssistantReply,
    CheckTool,
    ReadTool,
    ToolCall,
    ToolSpec,
    Turn,
)
from app.assistant.tools.toolbox import Card, Toolbox
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.category import Category
from app.models.receipt import ReceiptStatus
from app.models.user import User
from tests.factories.ai_usage import AiUsageFactory
from tests.factories.category import CategoryFactory
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

URL = "/api/v1/assistant"


class ScriptedAssistant:
    """Stands in for the model at the port: reads what it is told to, proposes cards."""

    def __init__(self, reads: Sequence[ToolCall] = (), proposals: Sequence[ToolCall] = ()):
        self.reads = list(reads)
        self.proposals = list(proposals)
        self.seen: list[Turn] = []
        self.read_results: list[str] = []

    async def reply(
        self,
        history: Sequence[Turn],
        tools: Sequence[ToolSpec],
        read: ReadTool,
        context: AssistantContext,
        check: CheckTool | None = None,
    ) -> AssistantReply:
        self.seen = list(history)
        self.read_results = [await read(call) for call in self.reads]
        return AssistantReply(f"answer in {context.language}", self.proposals)


async def _call(
    session: AsyncSession,
    user: User,
    method: str,
    url: str,
    json: Any = None,
    assistant: ScriptedAssistant | None = None,
) -> Response:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_assistant] = lambda: assistant or ScriptedAssistant()
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    current_user_id.set(user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.request(method, url, json=json)


async def _say(
    session: AsyncSession,
    user: User,
    text: str,
    assistant: ScriptedAssistant | None = None,
    conversation: str | None = None,
) -> dict[str, Any]:
    response = await _call(
        session,
        user,
        "POST",
        f"{URL}/messages",
        {"text": text, "conversation_id": conversation, "today": "2026-10-20"},
        assistant,
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


@pytest.mark.asyncio
async def test_a_conversation_is_kept_and_continues_where_it_was_left(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(language="uk")
    first = await _say(db_session, user, "What can you do?")
    assistant = ScriptedAssistant()

    second = await _say(db_session, user, "And now?", assistant, conversation=first["id"])
    listed = (await _call(db_session, user, "GET", f"{URL}/conversations")).json()

    assert first["title"] == "What can you do?"
    assert [(m["role"], m["text"]) for m in second["messages"]] == [
        ("user", "What can you do?"),
        ("assistant", "answer in uk"),
        ("user", "And now?"),
        ("assistant", "answer in uk"),
    ]
    assert [t.text for t in assistant.seen] == ["What can you do?", "answer in uk", "And now?"]
    assert [c["id"] for c in listed] == [first["id"]]


@pytest.mark.asyncio
async def test_a_read_tool_answers_from_the_users_own_month(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(budget_limit=Decimal("2000.00"))
    assistant = ScriptedAssistant(reads=[ToolCall("month_summary", {"month": "2026-10"})])

    await _say(db_session, user, "How am I doing?", assistant)

    assert '"budget": "2000.00"' in assistant.read_results[0]


@pytest.mark.asyncio
async def test_nothing_is_written_until_the_card_is_approved(db_session: AsyncSession) -> None:
    """ADR-0025: the model proposes; only the user's approval writes."""
    user = await UserFactory.create_async(budget_limit=None)
    assistant = ScriptedAssistant(proposals=[ToolCall("set_monthly_budget", {"amount": "2500"})])

    said = await _say(db_session, user, "Raise the budget to 2500", assistant)
    card = said["messages"][-1]
    await db_session.refresh(user)
    unchanged = user.budget_limit
    saved = await _call(
        db_session,
        user,
        "POST",
        f"{URL}/cards/{card['id']}/save",
        {"fields": {"amount": "2600"}},
    )
    await db_session.refresh(user)

    assert (card["card"], card["card_state"]) == (
        {"kind": "budget", "fields": {"amount": "2500"}, "form": None},
        "proposed",
    )
    assert unchanged is None
    assert (saved.status_code, saved.json()["card_state"]) == (200, "saved")
    assert user.budget_limit == Decimal("2600.00")


@pytest.mark.asyncio
async def test_an_approved_income_card_is_recorded_as_on_the_plan(
    db_session: AsyncSession,
) -> None:
    """With no card yet, the approved income makes "My card" to land on (F23.21)."""
    user = await UserFactory.create_async(language="en")
    assistant = ScriptedAssistant(
        proposals=[ToolCall("add_income", {"amount": "9000", "source": "Acme"})]
    )
    card = (await _say(db_session, user, "Salary came, 9000 from Acme", assistant))["messages"][-1]

    saved = await _call(
        db_session,
        user,
        "POST",
        f"{URL}/cards/{card['id']}/save",
        {"fields": card["card"]["fields"]},
    )
    month = (await _call(db_session, user, "GET", "/api/v1/income?month=2026-10")).json()

    assert card["card"]["fields"]["received_on"] == "2026-10-20"
    assert saved.json()["saved_ref"].startswith("income:")
    accounts = (await _call(db_session, user, "GET", "/api/v1/accounts")).json()["accounts"]
    assert [(e["source"], Decimal(e["amount"])) for e in month["entries"]] == [
        ("Acme", Decimal("9000.00"))
    ]
    assert [a["name"] for a in accounts] == ["My card"]


@pytest.mark.asyncio
async def test_a_card_is_done_once_and_bad_fields_are_refused(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    assistant = ScriptedAssistant(
        proposals=[ToolCall("add_bill", {"name": "Gym", "amount": "149"})]
    )
    card = (await _say(db_session, user, "Add the gym", assistant))["messages"][-1]

    bad = await _call(
        db_session, user, "POST", f"{URL}/cards/{card['id']}/save", {"fields": {"name": "Gym"}}
    )
    dismissed = await _call(db_session, user, "POST", f"{URL}/cards/{card['id']}/dismiss")
    again = await _call(
        db_session,
        user,
        "POST",
        f"{URL}/cards/{card['id']}/save",
        {"fields": card["card"]["fields"]},
    )

    assert bad.json()["code"] == "invalid_card"
    assert dismissed.json()["card_state"] == "dismissed"
    assert again.json()["code"] == "card_done"


@pytest.mark.asyncio
async def test_a_tool_the_assistant_was_never_given_proposes_nothing(
    db_session: AsyncSession,
) -> None:
    """Settings, the account and deleting have no tool: a made-up one is ignored."""
    user = await UserFactory.create_async()
    assistant = ScriptedAssistant(proposals=[ToolCall("delete_account", {})])

    said = await _say(db_session, user, "Delete my account", assistant)

    assert [m["card"] for m in said["messages"]] == [None, None]


@pytest.mark.asyncio
async def test_another_users_conversation_and_cards_are_not_found(
    db_session: AsyncSession,
) -> None:
    """N2: a conversation and its cards are their author's alone."""
    me = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    assistant = ScriptedAssistant(proposals=[ToolCall("set_monthly_budget", {"amount": "1"})])
    said = await _say(db_session, me, "Budget 1", assistant)
    card = said["messages"][-1]

    opened = await _call(db_session, stranger, "GET", f"{URL}/conversations/{said['id']}")
    listed = (await _call(db_session, stranger, "GET", f"{URL}/conversations")).json()
    saved = await _call(
        db_session, stranger, "POST", f"{URL}/cards/{card['id']}/save", {"fields": {"amount": "1"}}
    )
    continued = await _call(
        db_session,
        stranger,
        "POST",
        f"{URL}/messages",
        {"text": "hi", "conversation_id": said["id"]},
    )

    assert (opened.status_code, listed, saved.status_code, continued.status_code) == (
        404,
        [],
        404,
        404,
    )


@pytest.mark.asyncio
async def test_talking_is_paid_from_the_ai_credits(db_session: AsyncSession) -> None:
    """F21.9: a message costs what a message lately cost; none left, no model call."""
    user = await UserFactory.create_async()
    await AiUsageFactory.create_async(
        user_id=user.id,
        credits=Decimal(get_settings().free_monthly_credits),
        created_at=datetime.now(UTC),
    )
    assistant = ScriptedAssistant()

    response = await _call(db_session, user, "POST", f"{URL}/messages", {"text": "hi"}, assistant)

    assert (response.status_code, response.json()["code"]) == (429, "quota_exceeded")
    assert assistant.seen == []


@pytest.mark.asyncio
async def test_open_own_conversation_happy_path(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    said = await _say(db_session, user, "Hello assistant")
    res = await _call(db_session, user, "GET", f"{URL}/conversations/{said['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == said["id"]
    assert len(data["messages"]) == 2


@pytest.mark.asyncio
async def test_spending_by_category_read_tool(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    assistant = ScriptedAssistant(
        reads=[
            ToolCall("spending_by_category", {"month": "2026-10"}),
            ToolCall("spending_by_category", {}),
        ]
    )
    await _say(db_session, user, "Show spending by category", assistant)
    assert len(assistant.read_results) == 2
    assert "categories" in assistant.read_results[0]
    assert "2026-10" in assistant.read_results[0]
    assert "categories" in assistant.read_results[1]


@pytest.mark.asyncio
async def test_read_tool_error_handling(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    assistant = ScriptedAssistant(
        reads=[
            ToolCall("unknown_read_tool", {}),
            ToolCall("month_summary", {"month": "not-a-month"}),
        ]
    )
    await _say(db_session, user, "Read errors", assistant)
    assert len(assistant.read_results) == 2
    assert "no read tool" in assistant.read_results[0]
    assert "error" in assistant.read_results[1]


@pytest.mark.asyncio
async def test_bill_card_approval_and_persistence(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    assistant = ScriptedAssistant(
        proposals=[
            ToolCall("add_bill", {"name": "Internet", "amount": "80", "day": 15, "shared": False})
        ]
    )
    said = await _say(db_session, user, "Add Internet bill 80 on 15th", assistant)
    card = said["messages"][-1]
    assert card["card"]["kind"] == "bill"
    assert card["card"]["fields"]["name"] == "Internet"
    assert card["card"]["fields"]["day"] == 15
    assert card["card"]["fields"]["shared"] is False

    saved = await _call(
        db_session,
        user,
        "POST",
        f"{URL}/cards/{card['id']}/save",
        {"fields": card["card"]["fields"]},
    )
    assert saved.status_code == 200
    assert saved.json()["saved_ref"].startswith("bill:")


@pytest.mark.asyncio
async def test_non_existent_conversation_and_card_returns_404(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    random_id = uuid.uuid4()
    c_res = await _call(db_session, user, "GET", f"{URL}/conversations/{random_id}")
    assert c_res.status_code == 404

    s_res = await _call(db_session, user, "POST", f"{URL}/cards/{random_id}/save", {"fields": {}})
    assert s_res.status_code == 404

    d_res = await _call(db_session, user, "POST", f"{URL}/cards/{random_id}/dismiss")
    assert d_res.status_code == 404


@pytest.mark.asyncio
async def test_toolbox_save_unknown_card_kind_raises_domain_error(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    toolbox = Toolbox(db_session, user, date(2026, 10, 20))
    with pytest.raises(DomainError, match=r"This card cannot be saved\."):
        await toolbox.save(Card("unknown_kind", {}))


@pytest.mark.asyncio
async def test_a_free_message_may_take_fewer_rounds_than_a_paid_one(
    db_session: AsyncSession,
) -> None:
    """F21.9.2: one free message cannot spend the month in a long run of tool calls."""
    free = await UserFactory.create_async()
    admin = await UserFactory.create_async(role="admin")
    told: list[int] = []

    class Counting(ScriptedAssistant):
        async def reply(
            self, history: Any, tools: Any, read: Any, context: Any, check: Any = None
        ) -> Any:
            told.append(context.max_rounds)
            return await super().reply(history, tools, read, context, check)

    await _say(db_session, free, "hi", Counting())
    await _say(db_session, admin, "hi", Counting())

    assert told == [get_settings().free_assistant_rounds, AssistantContext.max_rounds]


@pytest.mark.asyncio
async def test_conversation_history_includes_card_states(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    # Step 1: create conversation with a proposal
    assistant1 = ScriptedAssistant(proposals=[ToolCall("set_monthly_budget", {"amount": "1500"})])
    conv = await _say(db_session, user, "Set budget 1500", assistant1)
    card1 = conv["messages"][-1]
    # Save the card
    await _call(
        db_session,
        user,
        "POST",
        f"{URL}/cards/{card1['id']}/save",
        {"fields": {"amount": "1500"}},
    )

    # Step 2: add another proposal and dismiss it
    assistant2 = ScriptedAssistant(
        proposals=[ToolCall("add_bill", {"name": "Streaming", "amount": "30"})]
    )
    conv2 = await _say(db_session, user, "Add Streaming", assistant2, conversation=conv["id"])
    card2 = conv2["messages"][-1]
    await _call(db_session, user, "POST", f"{URL}/cards/{card2['id']}/dismiss")

    # Step 3: send another message and inspect what history the assistant sees
    assistant3 = ScriptedAssistant()
    await _say(db_session, user, "What is my status?", assistant3, conversation=conv["id"])

    seen_texts = [t.text for t in assistant3.seen]
    assert any("approved by the user and saved" in text for text in seen_texts)
    assert any("dismissed by the user, nothing saved" in text for text in seen_texts)


@pytest.mark.asyncio
async def test_invalid_write_args_drops_proposal(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    assistant = ScriptedAssistant(
        proposals=[
            ToolCall("set_monthly_budget", {"amount": "-500"}),  # amount must be > 0
            ToolCall("add_income", {"amount": "0", "source": ""}),
        ]
    )
    said = await _say(db_session, user, "Invalid proposals", assistant)
    # Neither invalid proposal should produce a card message
    assert len(said["messages"]) == 2  # user + assistant text, no cards


@pytest.mark.asyncio
async def test_two_expenses_said_at_once_become_two_cards_and_count_once_approved(
    db_session: AsyncSession,
) -> None:
    """F21.3: 'yesterday taxi 45, coffee 12' — two cards, each in a category of the user's."""
    user = await UserFactory.create_async(currency="PLN")
    assistant = ScriptedAssistant(
        proposals=[
            ToolCall(
                "add_expense",
                {
                    "description": "Taxi",
                    "amount": "45",
                    "spent_on": "2026-10-19",
                    "category": "transport",
                },
            ),
            ToolCall("add_expense", {"description": "Coffee", "amount": "12", "category": "Cafés"}),
        ]
    )

    said = await _say(db_session, user, "Yesterday taxi 45, coffee 12", assistant)
    taxi, coffee = said["messages"][-2:]
    listed_before = (await _call(db_session, user, "GET", "/receipts")).json()
    saved = await _call(
        db_session,
        user,
        "POST",
        f"{URL}/cards/{taxi['id']}/save",
        {"fields": taxi["card"]["fields"]},
    )
    listed = (await _call(db_session, user, "GET", "/receipts")).json()

    assert (taxi["card"]["kind"], coffee["card"]["kind"]) == ("expense", "expense")
    assert taxi["card"]["fields"]["spent_on"] == "2026-10-19"
    assert coffee["card"]["fields"]["spent_on"] == "2026-10-20"
    # A category the user does not have falls back to Other rather than to nothing.
    assert coffee["card"]["fields"]["category_id"] is not None
    assert listed_before["items"] == []
    assert saved.json()["saved_ref"].startswith("receipt:")
    assert [(r["merchant_name"], Decimal(r["total_amount"])) for r in listed["items"]] == [
        ("Taxi", Decimal("45.00"))
    ]


@pytest.mark.asyncio
async def test_an_expense_card_never_saves_into_another_users_category(
    db_session: AsyncSession,
) -> None:
    """N2: the card's category is checked again when it is approved."""
    me = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    theirs = await CategoryFactory.create_async(user_id=stranger.id, name="Their secret")
    assistant = ScriptedAssistant(
        proposals=[ToolCall("add_expense", {"description": "X", "amount": "5"})]
    )
    card = (await _say(db_session, me, "X 5", assistant))["messages"][-1]

    saved = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/cards/{card['id']}/save",
        {"fields": {**card["card"]["fields"], "category_id": str(theirs.id)}},
    )

    assert saved.status_code == 404


async def _bought(
    user: User,
    day: date,
    shop: str,
    *lines: tuple[str, str],
    category: Category | None = None,
) -> None:
    receipt = await ReceiptFactory.create_async(
        user_id=user.id,
        merchant_name=shop,
        transaction_date=datetime(day.year, day.month, day.day, 12, tzinfo=UTC),
        total_amount=sum((Decimal(amount) for _, amount in lines), Decimal(0)),
        status=ReceiptStatus.PARSED,
        file_ids=[],
    )
    for name, amount in lines:
        await LineItemFactory.create_async(
            receipt=receipt,
            name=name,
            quantity=Decimal(1),
            unit_price=Decimal(amount),
            total_price=Decimal(amount),
            category=category,
        )


def _answers(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    return [m["card"]["fields"] for m in conversation["messages"] if m["card_state"] == "shown"]


@pytest.mark.asyncio
async def test_a_month_against_the_one_before_comes_with_its_chart_and_a_link(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    food = await CategoryFactory.create_async(user_id=user.id, name="Groceries")
    await _bought(user, date(2026, 10, 5), "Lidl", ("Mleko", "100.00"), category=food)
    await _bought(user, date(2026, 9, 5), "Lidl", ("Mleko", "60.00"), category=food)
    assistant = ScriptedAssistant(
        reads=[ToolCall("spending_by_category", {"month": "2026-10", "compare": True})]
    )

    conversation = await _say(db_session, user, "Groceries vs last month?", assistant)

    figures = json.loads(assistant.read_results[0])
    assert figures["spent"] == "100.00"
    assert figures["before"]["spent"] == "60.00"
    assert figures["categories"][0] == {"name": "Groceries", "spent": "100.00", "before": "60.00"}
    [card] = _answers(conversation)
    assert card["to"] == "/spending?start=2026-10-01&end=2026-10-31&compare=1"
    assert card["previous_start"] == "2026-09-01"
    assert card["chart"]["groups"][0]["name"] == "Groceries"


@pytest.mark.asyncio
async def test_a_shop_or_an_item_is_answered_from_the_users_own_receipts_only(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    other = await UserFactory.create_async()
    await _bought(user, date(2026, 10, 3), "Lidl Sp. z o.o.", ("Kawa", "20.00"), ("Chleb", "5.00"))
    await _bought(user, date(2026, 10, 9), "Biedronka", ("Kawa", "18.00"))
    await _bought(other, date(2026, 10, 4), "Lidl", ("Kawa", "999.00"))
    assistant = ScriptedAssistant(
        reads=[
            ToolCall("receipts", {"shop": "lidl", "month": "2026-10"}),
            ToolCall("receipts", {"item": "kawa", "month": "2026-10"}),
        ]
    )

    conversation = await _say(db_session, user, "Lidl and coffee this month?", assistant)

    shop, item = (json.loads(r) for r in assistant.read_results)
    assert (shop["receipts"], shop["spent"]) == (1, "25.00")
    assert (item["receipts"], item["spent_on_item"]) == (2, "38.00")
    assert [c["to"] for c in _answers(conversation)] == [
        "/receipts?start=2026-10-01&end=2026-10-31&q=kawa"
    ]


@pytest.mark.asyncio
async def test_a_products_prices_name_the_cheaper_shop_and_link_to_explore(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    other = await UserFactory.create_async()
    await _bought(user, date(2026, 10, 3), "Lidl", ("Mleko 2%", "3.49"))
    await _bought(user, date(2026, 10, 10), "Biedronka", ("Mleko 2%", "3.99"))
    await _bought(other, date(2026, 10, 10), "Żabka", ("Mleko 2%", "9.99"))
    assistant = ScriptedAssistant(reads=[ToolCall("product_prices", {"name": "mleko"})])

    conversation = await _say(db_session, user, "Where is milk cheapest?", assistant)

    [product] = json.loads(assistant.read_results[0])["products"]
    assert product["times_bought"] == 2
    assert {s["shop"]: s["latest"] for s in product["shops"]} == {
        "Lidl": "3.49",
        "Biedronka": "3.99",
    }
    [card] = _answers(conversation)
    assert card["to"].startswith("/products/explore?products=")


@pytest.mark.asyncio
async def test_a_period_ending_before_it_starts_is_told_back_not_raised(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    assistant = ScriptedAssistant(
        reads=[ToolCall("spending_by_category", {"start": "2026-10-20", "end": "2026-10-01"})]
    )

    conversation = await _say(db_session, user, "Spending?", assistant)

    assert "error" in assistant.read_results[0]
    assert _answers(conversation) == []
