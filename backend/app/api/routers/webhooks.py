"""Messages pushed to the API by infrastructure rather than by a signed-in user."""

import hmac
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.email_ingestion import EmailIngestionAdapter
from app.adapters.vision_agent import VisionAgentAdapter
from app.agent.factory import agent_from_settings
from app.api.dependencies import get_storage_service
from app.api.errors import AuthenticationError, MessageTooLargeError, NotFoundError
from app.api.routers.receipts import get_receipt_service
from app.core.config import get_settings
from app.db.session import get_db_session
from app.ports.storage import StoragePort
from app.schemas.webhook import InboundEmailResponse
from app.services.email_receipt import Accepted, InboundEmailService
from app.services.receipt import ReceiptService

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


def get_email_ingestion(
    storage: Annotated[StoragePort, Depends(get_storage_service)],
) -> EmailIngestionAdapter:
    """Provide the email channel; tests override this to stay off the network."""
    return EmailIngestionAdapter(storage, VisionAgentAdapter(agent_from_settings()))


@router.post(
    "/inbound-email",
    response_model=InboundEmailResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def inbound_email(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    ingestion: Annotated[EmailIngestionAdapter, Depends(get_email_ingestion)],
    receipts: Annotated[ReceiptService, Depends(get_receipt_service)],
    x_inbound_secret: Annotated[str | None, Header()] = None,
    x_inbound_recipient: Annotated[str, Header()] = "",
) -> InboundEmailResponse:
    """Take one raw message from the inbound mail relay and read it as a receipt (F11.2).

    The body is the message as received (RFC 5322) and `X-Inbound-Recipient` the
    address it was sent to. Only the relay knows `X-Inbound-Secret`; without it the
    answer is 401, and with no secret configured the endpoint does not exist (404).
    A dropped message is still a success to the relay, so it is not retried.
    """
    settings = get_settings()
    if settings.inbound_email_secret is None:
        raise NotFoundError("Not Found")
    expected = settings.inbound_email_secret.get_secret_value()
    if not x_inbound_secret or not hmac.compare_digest(x_inbound_secret, expected):
        raise AuthenticationError("The inbound mail secret is missing or wrong.")
    raw = await request.body()
    if len(raw) > settings.inbound_email_max_bytes:
        raise MessageTooLargeError("The message is larger than receipt intake accepts.")

    gate = InboundEmailService(
        session,
        domain=settings.inbound_email_domain,
        daily_limit=settings.inbound_email_daily_limit,
    )
    verdict = await gate.screen(raw, x_inbound_recipient, now=datetime.now(UTC))
    if not isinstance(verdict, Accepted):
        return InboundEmailResponse(status="dropped", reason=verdict.value)
    background_tasks.add_task(
        receipts.store_from_channel,
        verdict.user,
        ingestion,
        verdict.email,
        verdict.email.message_id,
    )
    return InboundEmailResponse(status="accepted")
