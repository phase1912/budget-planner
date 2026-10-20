"""Talking to the assistant (F21.1, F21.7, ADR-0025)."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.assistant_agent import AssistantAdapter
from app.agent.factory import agent_from_settings
from app.api import rate_limit
from app.api.dependencies import get_current_user, get_quota_service
from app.api.rate_limit import limiter
from app.db.session import get_db_session
from app.models.user import User
from app.ports.assistant import AssistantPort
from app.schemas.assistant import (
    CardFields,
    ConversationRead,
    ConversationSummary,
    MessageRead,
    SendRequest,
)
from app.services.assistant import AssistantService
from app.services.quota import QuotaService

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

CurrentUser = Annotated[User, Depends(get_current_user)]


def get_assistant() -> AssistantPort:
    """The assistant behind its port; tests put a scripted one in its place."""
    return AssistantAdapter(agent_from_settings())


def get_assistant_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    assistant: Annotated[AssistantPort, Depends(get_assistant)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
) -> AssistantService:
    """Conversations and cards, bound to the request's session."""
    return AssistantService(session, assistant, quota)


Service = Annotated[AssistantService, Depends(get_assistant_service)]


def _today(text: str | None) -> date:
    return date.fromisoformat(text) if text else datetime.now(UTC).date()


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(user: CurrentUser, service: Service) -> list[ConversationSummary]:
    """The caller's conversations, the latest touched first."""
    return [ConversationSummary.model_validate(c) for c in await service.conversations(user)]


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
async def open_conversation(
    conversation_id: uuid.UUID, user: CurrentUser, service: Service
) -> ConversationRead:
    """One conversation with its messages; 404 for another user's (N2)."""
    return ConversationRead.model_validate(await service.conversation(user, conversation_id))


@router.post("/messages", response_model=ConversationRead)
@limiter.limit(rate_limit.ASSISTANT)
async def send_message(
    request: Request, body: SendRequest, user: CurrentUser, service: Service
) -> ConversationRead:
    """Say something to the assistant and get its answer, with any cards it proposes.

    A new conversation when none is named. Counts against the monthly quota (F21.1):
    402 receipt_quota_exceeded when it is spent. Nothing is written but the messages.
    """
    conversation = await service.send(user, body.conversation_id, body.text, _today(body.today))
    return ConversationRead.model_validate(conversation)


@router.post("/cards/{message_id}/save", response_model=MessageRead)
async def save_card(
    message_id: uuid.UUID, body: CardFields, user: CurrentUser, service: Service
) -> MessageRead:
    """Approve a card as the user left it: only now is anything written (ADR-0025)."""
    return MessageRead.model_validate(
        await service.save_card(user, message_id, body.fields, _today(body.today))
    )


@router.post("/cards/{message_id}/dismiss", response_model=MessageRead)
async def dismiss_card(message_id: uuid.UUID, user: CurrentUser, service: Service) -> MessageRead:
    """Turn a card down; nothing is written."""
    return MessageRead.model_validate(await service.dismiss_card(user, message_id))
