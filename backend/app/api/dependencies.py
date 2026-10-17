import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.dns_mail_domains import DnsMailDomainResolver
from app.adapters.exchange_rates import (
    FallbackExchangeRates,
    FrankfurterExchangeRates,
    NbpExchangeRates,
)
from app.adapters.outgoing_mail import AppEngineMailSender, LogMailSender
from app.adapters.storage_factory import configured_storage
from app.api.errors import AuthenticationError, EmailNotConfirmedError, PermissionDeniedError
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.ports.email import EmailSenderPort
from app.ports.exchange_rates import ExchangeRatePort
from app.ports.mail_domains import MailDomainResolverPort
from app.ports.storage import StoragePort
from app.services.account import EmailAddressGuard
from app.services.activity import ActivityService
from app.services.mailer import Mailer
from app.services.quota import QuotaService, is_admin

"""API dependencies (F1.2.4)."""


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    token: str | None = None,
) -> User:
    """Dependency resolving the authenticated user from the Bearer token."""
    if not credentials and not token:
        raise AuthenticationError("Not authenticated.")

    actual_token = credentials.credentials if credentials else token
    assert actual_token is not None
    settings = get_settings()
    try:
        payload = jwt.decode(
            actual_token, settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"]
        )
        user_id_str: str | None = payload.get("sub")
        # A link from a letter is signed with the same key but is never a session.
        if user_id_str is None or "purpose" in payload:
            raise AuthenticationError("Invalid token.")
    except jwt.ExpiredSignatureError as err:
        raise AuthenticationError("Token expired.") from err
    except jwt.InvalidTokenError as err:
        raise AuthenticationError("Invalid token.") from err

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as err:
        raise AuthenticationError("Invalid user ID in token.") from err

    stmt = select(User).where(User.id == user_id)
    user = (await session.execute(stmt)).scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found.")

    ActivityService(session).seen(user.id, datetime.now(UTC).date())
    return user


async def get_confirmed_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    """The signed-in user, provided their address is confirmed (F17.8.2).

    Guards what an unconfirmed account may not do yet — upload receipts, invite to a
    household — with a code the client explains beside its offer to resend the link.
    """
    if not user.email_confirmed:
        raise EmailNotConfirmedError("Confirm your email address first: we sent you a link.")
    return user


async def get_admin_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    """The signed-in user, provided they are an admin (F17.3.3, F10.6.2).

    403 for anyone else. Being an admin opens the service's own figures and, later, the
    admin console (F18.6) — never another user's receipts (BRD N2).
    """
    if not is_admin(user, get_settings()):
        raise PermissionDeniedError("This page is for the service's administrators.")
    return user


def get_email_sender() -> EmailSenderPort:
    """Where letters go: the App Engine relay in a deployment, the log locally (ADR-0019)."""
    settings = get_settings()
    url = settings.mail_relay_send_url
    secret = settings.inbound_email_secret
    if url and secret:
        return AppEngineMailSender(url, secret.get_secret_value())
    return LogMailSender()


def get_mailer(sender: Annotated[EmailSenderPort, Depends(get_email_sender)]) -> Mailer:
    """Delivers letters in the background, retrying (F17.8.1)."""
    return Mailer(sender)


def get_mail_domain_resolver() -> MailDomainResolverPort | None:
    """DNS lookups for sign-up's address check, unless the check is switched off."""
    return DnsMailDomainResolver() if get_settings().email_domain_dns_check else None


def get_email_guard(
    resolver: Annotated[MailDomainResolverPort | None, Depends(get_mail_domain_resolver)],
) -> EmailAddressGuard:
    """Refuses throwaway and undeliverable addresses (F17.8.4)."""
    return EmailAddressGuard(resolver)


async def get_storage_service() -> AsyncGenerator[StoragePort, None]:
    """The configured StoragePort: S3-compatible, or Cloud Storage (ADR-0014)."""
    async with configured_storage() as service:
        yield service


def get_quota_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> QuotaService:
    """The receipt quota (F10.6); tests override it where they have no real database."""
    return QuotaService(session, get_settings())


def get_exchange_rates() -> ExchangeRatePort | None:
    """Rates for converting foreign receipts (F11.7, ADR-0016); None when switched off."""
    if get_settings().exchange_rate_source == "off":
        return None
    return FallbackExchangeRates(NbpExchangeRates(), FrankfurterExchangeRates())
