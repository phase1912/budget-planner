"""Talking to the assistant, against a real database and a scripted model (F21.1, F21.7, N2)."""

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
from app.api.routers.assistant import get_assistant
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.user import User
from app.ports.assistant import (
    AssistantContext,
    AssistantReply,
    CheckTool,
    ReadTool,
    ToolCall,
    ToolSpec,
    Turn,
)
from app.services.assistant_tools import Card, Toolbox
from app.services.quota import QuotaService
from tests.factories.category import CategoryFactory
from tests.factories.upload_job import UploadJobFactory
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
        {"kind": "budget", "fields": {"amount": "2500"}},
        "proposed",
    )
    assert unchanged is None
    assert (saved.status_code, saved.json()["card_state"]) == (200, "saved")
    assert user.budget_limit == Decimal("2600.00")


@pytest.mark.asyncio
async def test_an_approved_income_card_is_recorded_as_on_the_plan(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
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
    assert [(e["source"], Decimal(e["amount"])) for e in month["entries"]] == [
        ("Acme", Decimal("9000.00"))
    ]


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
async def test_talking_counts_against_the_months_quota(db_session: AsyncSession) -> None:
    """F21.1: every started batch of messages costs one read; none left, no model call."""
    user = await UserFactory.create_async()
    await UploadJobFactory.create_async(
        user_id=user.id,
        total_items=get_settings().monthly_receipt_quota,
        created_at=datetime.now(UTC),
    )
    assistant = ScriptedAssistant()

    response = await _call(db_session, user, "POST", f"{URL}/messages", {"text": "hi"}, assistant)

    assert response.status_code == 429
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
async def test_quota_service_counts_assistant_messages(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    quota_svc = QuotaService(db_session, get_settings())
    before = await quota_svc.quota_for(user, datetime.now(UTC))
    assert before.used == 0

    await _say(db_session, user, "Hello assistant")
    after = await quota_svc.quota_for(user, datetime.now(UTC))
    # 1 message sent -> 1 read used (since 1 message // per_read rounded up is 1 read)
    assert after.used == 1


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
