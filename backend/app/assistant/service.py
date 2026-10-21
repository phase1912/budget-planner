"""Talking to the assistant: conversations, messages and the cards it proposes
(F21.1, F21.7, ADR-0025, ADR-0028)."""

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError, NotFoundError, ProblemCode
from app.assistant.core.ports import AssistantContext, AssistantPort, Turn
from app.assistant.tools.toolbox import Card, Toolbox, tool_specs
from app.models.conversation import Conversation, ConversationMessage
from app.models.user import User
from app.ports.exchange_rates import ExchangeRatePort
from app.ports.goal_mapping import GoalMapperPort
from app.services.quota import QuotaService

TITLE_LENGTH = 120


class CardState:
    """Where a proposed card is: waiting for the user, written, or turned down."""

    PROPOSED = "proposed"
    SAVED = "saved"
    DISMISSED = "dismissed"
    SHOWN = "shown"
    """An answer card (F21.4): a chart or a link shown with an answer, nothing to approve."""


class AssistantService:
    """The user's conversations with the assistant, and every card's way to being saved.

    Every message the user sends is a model call and counts against their monthly
    reading quota (F21.1, `QuotaService`); reading a conversation does not. Cards are
    written only when the user saves them, through `Toolbox.save` (ADR-0025).
    """

    def __init__(
        self,
        session: AsyncSession,
        assistant: AssistantPort,
        quota: QuotaService,
        rates: ExchangeRatePort | None = None,
        goal_mapper: GoalMapperPort | None = None,
    ) -> None:
        self.session = session
        self.assistant = assistant
        self.quota = quota
        self.rates = rates
        self.goal_mapper = goal_mapper

    async def conversations(self, user: User) -> Sequence[Conversation]:
        """The user's conversations, the latest touched first."""
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def conversation(self, user: User, conversation_id: uuid.UUID) -> Conversation:
        """One of the user's conversations with its messages; NotFoundError otherwise (N2)."""
        found = await self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user.id
            )
        )
        if found is None:
            raise NotFoundError("No such conversation.")
        return found

    async def send(
        self, user: User, conversation_id: uuid.UUID | None, text: str, today: date
    ) -> Conversation:
        """Add the user's message and the assistant's answer, with any cards it proposes.

        A new conversation is started when none is named, titled by this first message.
        Raises ReceiptQuotaExceededError before any model call when the month's quota is
        spent, like reading a receipt would.
        """
        await self.quota.ensure_can_talk(user, datetime.now(UTC))
        conversation = (
            await self.conversation(user, conversation_id)
            if conversation_id
            else Conversation(user_id=user.id, title=text.strip()[:TITLE_LENGTH], messages=[])
        )
        if conversation_id is None:
            self.session.add(conversation)
        conversation.messages.append(
            ConversationMessage(user_id=user.id, role="user", text=text.strip())
        )
        toolbox = self._toolbox(user, today)
        reply = await self.assistant.reply(
            _history(conversation.messages),
            tool_specs(),
            toolbox.read,
            AssistantContext(
                user.language or "en",
                user.currency,
                today.isoformat(),
                tuple(c.name for c in await toolbox.categories()),
            ),
            toolbox.check,
        )
        conversation.messages.append(
            ConversationMessage(user_id=user.id, role="assistant", text=reply.text)
        )
        for answer in toolbox.answers.values():
            conversation.messages.append(
                ConversationMessage(
                    user_id=user.id,
                    role="assistant",
                    text="",
                    card={"kind": answer.kind, "fields": answer.fields},
                    card_state=CardState.SHOWN,
                )
            )
        for proposal in reply.proposals:
            card = await toolbox.propose(proposal)
            if card is not None:
                conversation.messages.append(
                    ConversationMessage(
                        user_id=user.id,
                        role="assistant",
                        text="",
                        card={"kind": card.kind, "fields": card.fields},
                        card_state=CardState.PROPOSED,
                    )
                )
        conversation.updated_at = datetime.now(UTC)
        await self.session.flush()
        return conversation

    async def save_card(
        self, user: User, message_id: uuid.UUID, fields: dict[str, Any], today: date
    ) -> ConversationMessage:
        """Write a proposed card as the user left it; only then is anything changed.

        Raises NotFoundError for another user's card (N2), DomainError (card_done) for one
        already saved or dismissed, and the service's own refusals for fields that do not
        hold.
        """
        message = await self._card(user, message_id)
        card = Card(str(message.card["kind"]) if message.card else "", fields)
        message.saved_ref = await self._toolbox(user, today).save(card)
        message.card = {"kind": card.kind, "fields": fields}
        message.card_state = CardState.SAVED
        await self.session.flush()
        return message

    def _toolbox(self, user: User, today: date) -> Toolbox:
        return Toolbox(self.session, user, today, self.rates, self.goal_mapper)

    async def dismiss_card(self, user: User, message_id: uuid.UUID) -> ConversationMessage:
        """Turn a proposed card down; nothing is written."""
        message = await self._card(user, message_id)
        message.card_state = CardState.DISMISSED
        await self.session.flush()
        return message

    async def _card(self, user: User, message_id: uuid.UUID) -> ConversationMessage:
        message = await self.session.scalar(
            select(ConversationMessage).where(
                ConversationMessage.id == message_id, ConversationMessage.user_id == user.id
            )
        )
        if message is None or message.card is None:
            raise NotFoundError("No such card.")
        if message.card_state != CardState.PROPOSED:
            raise DomainError("This card is already done.", code=ProblemCode.CARD_DONE)
        return message


CARD_STATES = {
    CardState.PROPOSED: "proposed to the user, NOT saved yet",
    CardState.SAVED: "approved by the user and saved",
    CardState.DISMISSED: "dismissed by the user, nothing saved",
}


def _history(messages: Sequence[ConversationMessage]) -> list[Turn]:
    """The conversation as the assistant reads it: text, and each card by what became of it.

    Saying plainly whether a card was saved keeps the model from taking a proposal for a
    done thing — or from answering a new request with words instead of a new card.
    """
    turns: list[Turn] = []
    for m in messages:
        role: Literal["user", "assistant"] = "user" if m.role == "user" else "assistant"
        if m.card_state == CardState.SHOWN:
            # The answer beside it already says what the chart or link shows.
            continue
        if m.card is not None:
            state = CARD_STATES.get(m.card_state or "", "")
            text = f"(A {m.card.get('kind')} card, {state}: {m.card.get('fields')})"
        elif m.text:
            text = m.text
        else:
            continue
        # Small models lose their way on two answers in a row: a card joins the answer
        # it came with.
        if turns and turns[-1].role == role == "assistant":
            turns[-1] = Turn("assistant", f"{turns[-1].text} {text}")
        else:
            turns.append(Turn(role, text))
    return turns
