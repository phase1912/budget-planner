"""Contact form (F17.10.2)."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.api import rate_limit
from app.api.dependencies import get_mailer
from app.api.rate_limit import limiter
from app.core.config import get_settings
from app.schemas.auth import MessageResponse
from app.schemas.contact import ContactRequest
from app.services.contact import THROTTLE, ContactMessage, contact_letters
from app.services.mailer import Mailer

router = APIRouter(prefix="/api/v1/contact", tags=["contact"])


@router.post("", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(rate_limit.CONTACT)
async def contact(
    request: Request,
    body: ContactRequest,
    mailer: Annotated[Mailer, Depends(get_mailer)],
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    """Mail the message to the support mailbox, with the sender to reply to (F17.10.2).

    The support mailbox (F22.1.2) when one is set, else the administrators.

    No address is published and no domain is needed: it goes out like every letter
    (ADR-0019). A filled-in trap field is answered as a success and sent nowhere, so a
    bot learns nothing; 429 for an address that wrote too often.
    """
    accepted = MessageResponse(message="Your message is on its way. A copy is in your inbox.")
    if body.website:
        return accepted
    THROTTLE.admit(body.email)
    message = ContactMessage(body.email, body.topic, body.message.strip(), body.language)
    settings = get_settings()
    recipients = [settings.support_email] if settings.support_email else settings.admin_emails
    for letter in contact_letters(message, recipients):
        background_tasks.add_task(mailer.deliver, letter)
    return accepted
