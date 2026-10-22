"""Unit tests for AssistantService (F21.1, ADR-0025, N2)."""

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError, NotFoundError
from app.assistant.core.ports import (
    AssistantContext,
    AssistantReply,
    CheckTool,
    ReadTool,
    ToolCall,
    ToolSpec,
    Turn,
)
from app.assistant.service import AssistantService, CardState, _history
from app.assistant.tools.budget import BudgetArgs
from app.assistant.tools.toolbox import Toolbox
from app.core.config import get_settings
from app.core.context import current_user_id
from app.models.conversation import ConversationMessage
from app.services.quota import QuotaService
from tests.factories.user import UserFactory


class StubAssistant:
    """Scripted assistant port for unit tests."""

    def __init__(self, reply_text: str = "ok", proposals: list[ToolCall] | None = None) -> None:
        self.reply_text = reply_text
        self.proposals = proposals or []

    async def reply(
        self,
        history: Sequence[Turn],
        tools: Sequence[ToolSpec],
        read: ReadTool,
        context: AssistantContext,
        check: CheckTool | None = None,
    ) -> AssistantReply:
        return AssistantReply(self.reply_text, self.proposals)


@pytest.mark.asyncio
async def test_assistant_service_send_and_retrieve_conversation(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)  # as signing in sets it for a request
    quota = QuotaService(db_session, get_settings())
    stub = StubAssistant(
        reply_text="Budget proposed",
        proposals=[ToolCall("set_monthly_budget", {"amount": "1200.00"})],
    )
    service = AssistantService(db_session, stub, quota)
    today = date(2026, 10, 20)

    # 1. Start new conversation
    conv = await service.send(user, None, "Set budget to 1200", today)
    assert conv.title == "Set budget to 1200"
    assert len(conv.messages) == 3  # user, assistant text, assistant card proposal
    assert conv.messages[0].role == "user"
    assert conv.messages[1].role == "assistant"
    assert conv.messages[2].role == "assistant"
    assert conv.messages[2].card_state == CardState.PROPOSED

    # 2. Retrieve existing conversation
    fetched = await service.conversation(user, conv.id)
    assert fetched.id == conv.id

    # 3. Retrieve non-existent or other user's conversation
    other_user = await UserFactory.create_async()
    with pytest.raises(NotFoundError):
        await service.conversation(other_user, conv.id)

    with pytest.raises(NotFoundError):
        await service.conversation(user, uuid.uuid4())

    # 4. Continue existing conversation
    stub.proposals = []
    stub.reply_text = "Noted!"
    conv2 = await service.send(user, conv.id, "Thanks", today)
    assert len(conv2.messages) == 5  # added user + assistant

    # 5. List conversations
    listed = await service.conversations(user)
    assert len(listed) == 1
    assert listed[0].id == conv.id


@pytest.mark.asyncio
async def test_assistant_service_card_lifecycle(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    current_user_id.set(user.id)
    quota = QuotaService(db_session, get_settings())
    stub = StubAssistant(
        reply_text="Here is your budget card",
        proposals=[ToolCall("set_monthly_budget", {"amount": "3000.00"})],
    )
    service = AssistantService(db_session, stub, quota)
    today = date(2026, 10, 20)

    conv = await service.send(user, None, "Budget 3000", today)
    card_msg = conv.messages[-1]
    assert card_msg.card_state == CardState.PROPOSED

    # Save the card
    saved_msg = await service.save_card(user, card_msg.id, {"amount": "3000.00"}, today)
    assert saved_msg.card_state == CardState.SAVED
    assert saved_msg.saved_ref == "plan:budget"
    await db_session.refresh(user)
    assert user.budget_limit == Decimal("3000.00")

    # Cannot save or dismiss an already saved card
    with pytest.raises(DomainError):
        await service.save_card(user, card_msg.id, {"amount": "3000.00"}, today)

    with pytest.raises(DomainError):
        await service.dismiss_card(user, card_msg.id)

    # Dismiss card on a new proposal
    conv2 = await service.send(user, None, "Another card", today)
    card_msg2 = conv2.messages[-1]
    dismissed_msg = await service.dismiss_card(user, card_msg2.id)
    assert dismissed_msg.card_state == CardState.DISMISSED

    # Cannot save or dismiss again
    with pytest.raises(DomainError):
        await service.dismiss_card(user, card_msg2.id)

    # Non-existent card
    with pytest.raises(NotFoundError):
        await service.save_card(user, uuid.uuid4(), {}, today)
    with pytest.raises(NotFoundError):
        await service.dismiss_card(user, uuid.uuid4())


def test_history_builder_formatting() -> None:
    uid = uuid.uuid4()
    messages = [
        ConversationMessage(user_id=uid, role="user", text="Hello"),
        ConversationMessage(user_id=uid, role="assistant", text="Hi there"),
        ConversationMessage(
            user_id=uid,
            role="assistant",
            text="",
            card={"kind": "budget", "fields": {"amount": "1000"}},
            card_state=CardState.SAVED,
        ),
        ConversationMessage(user_id=uid, role="assistant", text=""),  # empty text & no card
    ]
    turns = _history(messages)
    assert len(turns) == 2
    assert turns[0].role == "user"
    assert turns[0].text == "Hello"
    assert turns[1].role == "assistant"
    assert "Hi there" in turns[1].text
    assert "approved by the user and saved" in turns[1].text


@pytest.mark.parametrize(
    ("written", "amount"),
    [
        ("2 500", "2500"),
        ("2500 zł", "2500"),
        ("12,50", "12.50"),
        ("1,234.50", "1234.50"),
        ("1.234,50", "1234.50"),
        (2500, "2500"),
    ],
)
def test_an_amount_spelled_as_people_write_it_still_makes_a_card(
    written: object, amount: str
) -> None:
    assert BudgetArgs.model_validate({"amount": written}).amount == Decimal(amount)


@pytest.mark.asyncio
async def test_a_write_call_that_cannot_be_a_card_says_why() -> None:
    toolbox = Toolbox(None, None, date(2026, 10, 20))  # type: ignore[arg-type]
    assert await toolbox.check(ToolCall("set_monthly_budget", {"amount": "2 500"})) is None
    assert "amount" in (await toolbox.check(ToolCall("set_monthly_budget", {})) or "")
    assert await toolbox.check(ToolCall("delete_account", {})) == "no write tool delete_account"
