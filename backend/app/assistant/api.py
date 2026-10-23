"""Talking to the assistant over HTTP (F21.1, F21.7, ADR-0025, ADR-0028)."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.speech import ChirpSpeechAdapter, ModelSpeechAdapter
from app.agent.factory import agent_from_settings
from app.api import rate_limit
from app.api.dependencies import (
    get_current_user,
    get_exchange_rates,
    get_mailer,
    get_quota_service,
    get_session_second_factor,
    get_storage_service,
)
from app.api.errors import (
    SpeechTooLongError,
    SpeechUnavailableError,
    UnsupportedFileFormatError,
)
from app.api.rate_limit import limiter
from app.api.routers.goals import get_goal_mapper
from app.api.routers.receipts import get_item_categoriser
from app.api.routers.recommendations import get_advice_generator
from app.assistant.core.graph import AssistantGraph
from app.assistant.core.ports import AssistantPort
from app.assistant.schemas import (
    CardFields,
    ConversationRead,
    ConversationSummary,
    MessageRead,
    ReportRequest,
    SendRequest,
    SpeechRead,
)
from app.assistant.service import AssistantService
from app.assistant.tools.base import Access
from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.speech import MAX_SECONDS, NotWav, wav_seconds
from app.models.user import User
from app.ports.advice_generation import AdviceGeneratorPort
from app.ports.categorisation import ItemCategoriserPort
from app.ports.exchange_rates import ExchangeRatePort
from app.ports.goal_mapping import GoalMapperPort
from app.ports.speech import SpeechPort, SpeechUnavailable
from app.ports.storage import StoragePort
from app.services.ai_usage import record_usage
from app.services.mailer import Mailer
from app.services.quota import QuotaService, is_admin, is_super_admin

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

CurrentUser = Annotated[User, Depends(get_current_user)]


SPEECH_BYTES = 2_000_000
"""A minute of the 16 kHz mono WAV the microphone records, and a little over."""


def get_assistant() -> AssistantPort:
    """The assistant behind its port; tests put a scripted one in its place."""
    return AssistantGraph(agent_from_settings())


def get_speech() -> SpeechPort:
    """The recogniser the deployment chose (ADR-0031); tests put a stub in its place."""
    settings = get_settings()
    if settings.speech_engine == "speech_to_text" and settings.vertex_project:
        return ChirpSpeechAdapter(
            settings.vertex_project, settings.speech_location, recorder=record_usage
        )
    return ModelSpeechAdapter(agent_from_settings())


def get_assistant_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    assistant: Annotated[AssistantPort, Depends(get_assistant)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
    rates: Annotated[ExchangeRatePort | None, Depends(get_exchange_rates)],
    goal_mapper: Annotated[GoalMapperPort, Depends(get_goal_mapper)],
    advice: Annotated[AdviceGeneratorPort, Depends(get_advice_generator)],
    storage: Annotated[StoragePort, Depends(get_storage_service)],
    categoriser: Annotated[ItemCategoriserPort, Depends(get_item_categoriser)],
    user: Annotated[User, Depends(get_current_user)],
    second_factor: Annotated[bool, Depends(get_session_second_factor)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> AssistantService:
    """Conversations and cards, bound to the request's session; an admin's tools only for
    an admin whose session was opened with a second factor (F21.12, F18.6.1)."""
    return AssistantService(
        session,
        assistant,
        quota,
        rates,
        goal_mapper,
        advice,
        storage,
        categoriser,
        session_access(user, second_factor),
        mailer,
    )


def session_access(user: User, second_factor: bool) -> Access:
    """Who the session is to the assistant's tools: as the admin pages decide (F18.6.1)."""
    settings = get_settings()
    if not is_admin(user, settings) or (
        settings.requires_admin_second_factor and not second_factor
    ):
        return "user"
    return "super_admin" if is_super_admin(user, settings) else "admin"


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
    402 receipt_quota_exceeded when it is spent. Nothing is written but the messages. Files
    sent with it were uploaded first, as from the Add screen; their reading is named here and
    must be the user's own (404 otherwise, N2).
    """
    conversation = await service.send(
        user,
        body.conversation_id,
        body.text,
        _today(body.today),
        attachment=(body.upload_job_id, body.attached) if body.upload_job_id else None,
    )
    return ConversationRead.model_validate(conversation)


@router.post("/speech", response_model=SpeechRead)
@limiter.limit(rate_limit.SPEECH)
async def recognise_speech(
    request: Request,
    audio: UploadFile,
    user: CurrentUser,
    speech: Annotated[SpeechPort, Depends(get_speech)],
    quota: Annotated[QuotaService, Depends(get_quota_service)],
) -> SpeechRead:
    """The words said in a recording from the microphone (F21.2.2), for the user to send.

    Only the WAV the microphone makes, a minute at most by its own length (F21.9.4):
    415 for anything else, 413 speech_too_long past the minute — whatever the file's
    size. Paid from the AI credits by its seconds (429 quota_exceeded when spent).
    Recognised by Google Cloud and dropped: nothing of the sound is stored; 503
    speech_unavailable when the recogniser fails.
    """
    sound = await audio.read(SPEECH_BYTES + 1)
    try:
        seconds = wav_seconds(sound)
    except NotWav as exc:
        raise UnsupportedFileFormatError("Send the recording as a WAV.") from exc
    if len(sound) > SPEECH_BYTES or seconds > MAX_SECONDS:
        raise SpeechTooLongError("A recording can be a minute long at most.")
    await quota.ensure_can_speak(user, seconds, datetime.now(UTC))
    try:
        text = await speech.recognise(sound, "audio/wav", user.language or "en")
    except SpeechUnavailable as exc:
        raise SpeechUnavailableError("The speech could not be recognised just now.") from exc
    return SpeechRead(text=text)


@router.post("/cards/{message_id}/save", response_model=MessageRead)
async def save_card(
    message_id: uuid.UUID, body: CardFields, user: CurrentUser, service: Service
) -> MessageRead:
    """Approve a card as the user left it: only now is anything written (ADR-0025)."""
    return MessageRead.model_validate(
        await service.save_card(user, message_id, body.fields, _today(body.today))
    )


@router.post("/messages/{message_id}/report", status_code=204)
async def report_reply(
    message_id: uuid.UUID, body: ReportRequest, user: CurrentUser, service: Service
) -> Response:
    """Report an assistant reply as offensive, wrong or otherwise (F22.4.2)."""
    await service.report(user, message_id, body.reason)
    return Response(status_code=204)


@router.post("/cards/{message_id}/dismiss", response_model=MessageRead)
async def dismiss_card(message_id: uuid.UUID, user: CurrentUser, service: Service) -> MessageRead:
    """Turn a card down; nothing is written."""
    return MessageRead.model_validate(await service.dismiss_card(user, message_id))
