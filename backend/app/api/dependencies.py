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
from app.adapters.oidc import AppleTokens, JwksIdTokenVerifier
from app.adapters.outgoing_mail import AppEngineMailSender, LogMailSender
from app.adapters.storage_factory import configured_storage
from app.api.errors import (
    AuthenticationError,
    EmailNotConfirmedError,
    PermissionDeniedError,
    ProblemCode,
)
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.ports.email import EmailSenderPort
from app.ports.exchange_rates import ExchangeRatePort
from app.ports.mail_domains import MailDomainResolverPort
from app.ports.sign_in import AppleTokensPort, IdTokenVerifierPort
from app.ports.storage import StoragePort
from app.services.account import EmailAddressGuard
from app.services.activity import ActivityService
from app.services.mailer import Mailer
from app.services.quota import QuotaService, is_admin, is_super_admin
from app.services.sign_in import SignInService

"""API dependencies (F1.2.4)."""


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
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


def get_session_second_factor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> bool:
    """Whether the caller's session was opened with an authenticator code (F18.6.1)."""
    if credentials is None:
        return False
    try:
        claims = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret_key.get_secret_value(),
            algorithms=["HS256"],
        )
    except jwt.InvalidTokenError:
        return False
    return claims.get("sf") is True


async def get_admin_user(
    user: Annotated[User, Depends(get_current_user)],
    second_factor: Annotated[bool, Depends(get_session_second_factor)],
) -> User:
    """The signed-in user, provided they are an admin who signed in with a second factor.

    403 for anyone else (F17.3.3, F18.6); 403 second_factor_required for an admin whose
    session was opened with the password alone, where the deployment asks for more
    (F18.6.1). Being an admin never opens another user's receipts (BRD N2).
    """
    settings = get_settings()
    if not is_admin(user, settings):
        raise PermissionDeniedError("This page is for the service's administrators.")
    if settings.requires_admin_second_factor and not second_factor:
        raise PermissionDeniedError(
            "Turn on two-factor sign-in and sign in with it to open the admin pages.",
            code=ProblemCode.SECOND_FACTOR_REQUIRED,
        )
    return user


async def get_super_admin(user: Annotated[User, Depends(get_admin_user)]) -> User:
    """An admin who is also a super admin: 403 super_admin_only for any other (F18.6.1)."""
    if not is_super_admin(user, get_settings()):
        raise PermissionDeniedError(
            "Only a super admin can do this.", code=ProblemCode.SUPER_ADMIN_ONLY
        )
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
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> QuotaService:
    """The AI credit wallet (F10.6, F21.9); tests override it where they have no database."""
    return QuotaService(session, get_settings())


def get_exchange_rates() -> ExchangeRatePort | None:
    """Rates for converting foreign receipts (F11.7, ADR-0016); None when switched off."""
    if get_settings().exchange_rate_source == "off":
        return None
    return FallbackExchangeRates(NbpExchangeRates(), FrankfurterExchangeRates())


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> User | None:
    """The signed-in user when a session token is sent, else None (F1.6: linking)."""
    if credentials is None:
        return None
    return await get_current_user(credentials, session)


_verifiers: dict[tuple[tuple[str, ...], tuple[str, ...]], JwksIdTokenVerifier] = {}


def get_id_token_verifier() -> IdTokenVerifierPort:
    """Google's and Apple's key sets, kept between requests for the configured client ids."""
    settings = get_settings()
    key = (tuple(settings.google_client_ids), tuple(settings.apple_client_ids))
    if key not in _verifiers:
        _verifiers[key] = JwksIdTokenVerifier(
            {"google": settings.google_client_ids, "apple": settings.apple_client_ids}
        )
    return _verifiers[key]


def get_apple_tokens() -> AppleTokensPort:
    """Apple's token endpoints, signed with the key from Secret Manager (F1.6.3)."""
    settings = get_settings()
    key = settings.apple_private_key
    return AppleTokens(
        settings.apple_team_id, settings.apple_key_id, key.get_secret_value() if key else None
    )


def get_sign_in_service(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
    verifier: Annotated[IdTokenVerifierPort, Depends(get_id_token_verifier)],
    apple_tokens: Annotated[AppleTokensPort, Depends(get_apple_tokens)],
) -> SignInService:
    """Signing in with Google and Apple (F1.6); tests override the verifier with their keys."""
    return SignInService(session, verifier, apple_tokens, get_settings())
