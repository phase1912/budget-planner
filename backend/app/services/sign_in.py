"""Signing in with Google and Apple (F1.6, ADR-0035)."""

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cryptography.fernet import InvalidToken as InvalidFernetToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import (
    AuthenticationError,
    DomainError,
    NotFoundError,
    ProblemCode,
    RegistrationError,
)
from app.core.config import Settings
from app.core.security import decrypt_secret, encrypt_secret, get_password_hash, verify_password
from app.domain.activity import ActivityKind
from app.domain.terms import TERMS_VERSION
from app.models.linked_identity import LinkedIdentity
from app.models.user import User
from app.ports.sign_in import (
    AppleTokensPort,
    IdTokenVerifierPort,
    InvalidIdToken,
    Provider,
    VerifiedIdentity,
)
from app.repository.user import UserRepository
from app.services.activity import ActivityService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderSignIn:
    """What the client sends after the provider's sign-in (F1.6.1).

    `password` links an existing account with the same address, proving it is theirs;
    `accept_terms` opens a new one. `first_name`/`last_name` are Apple's, given to the
    client on the first sign-in only. `authorization_code` lets the server keep Apple's
    refresh token, to revoke it when the account is deleted (F1.6.3).
    """

    id_token: str
    nonce: str
    password: str | None = None
    accept_terms: bool = False
    first_name: str | None = None
    last_name: str | None = None
    authorization_code: str | None = None


class SignInService:
    """Signs in, opens or links accounts from a provider's verified ID token (F1.6).

    An address that already has an account is never linked silently: its password is
    asked for once (or the user is already signed in to it). A provider account signs in
    to one user only (BRD N2).
    """

    def __init__(
        self,
        session: AsyncSession,
        verifier: IdTokenVerifierPort,
        apple_tokens: AppleTokensPort,
        settings: Settings,
    ) -> None:
        self.session = session
        self.verifier = verifier
        self.apple_tokens = apple_tokens
        self.settings = settings
        self.users = UserRepository(session)

    def client_ids(self) -> dict[Provider, str | None]:
        """The client id the web opens each provider with; None for a provider switched off."""
        google = self.settings.google_client_ids
        apple = self.settings.apple_client_ids
        return {"google": google[0] if google else None, "apple": apple[0] if apple else None}

    async def sign_in(
        self, provider: Provider, request: ProviderSignIn, current: User | None = None
    ) -> tuple[User, bool]:
        """The account the token signs in to, and whether it was opened just now.

        Signed in already (`current`), the provider is linked to that account. Raises
        NotFoundError (sign_in_provider_off) for a provider without client ids,
        AuthenticationError (id_token_invalid, provider_email_unverified, or
        invalid_credentials for a wrong password), DomainError (link_needs_password,
        identity_taken) and RegistrationError (terms_required).
        """
        if self.client_ids()[provider] is None:
            raise NotFoundError(
                "Signing in with this provider is off.", code=ProblemCode.SIGN_IN_PROVIDER_OFF
            )
        try:
            identity = await self.verifier.verify(provider, request.id_token, request.nonce)
        except InvalidIdToken as err:
            raise AuthenticationError(
                "The sign-in could not be checked.", code=ProblemCode.ID_TOKEN_INVALID
            ) from err

        linked = await self._linked(provider, identity.subject)
        if linked is not None:
            if current is not None and linked.user_id != current.id:
                raise DomainError(
                    "That account signs in to another account.", code=ProblemCode.IDENTITY_TAKEN
                )
            user = await self.session.get(User, linked.user_id)
            assert user is not None
            return user, False

        if current is not None:
            await self._link(current, identity, request)
            return current, False

        if not identity.email_verified:
            raise AuthenticationError(
                "The provider has not confirmed this address.",
                code=ProblemCode.PROVIDER_EMAIL_UNVERIFIED,
            )
        existing = await self.users.get_by_email(identity.email)
        if existing is not None:
            if request.password is None:
                raise DomainError(
                    "An account with this address exists; its password links it.",
                    code=ProblemCode.LINK_NEEDS_PASSWORD,
                )
            if not existing.password_set or not verify_password(
                request.password, existing.password_hash
            ):
                raise AuthenticationError(
                    "Invalid email or password.", code=ProblemCode.INVALID_CREDENTIALS
                )
            await self._link(existing, identity, request)
            return existing, False

        return await self._open(identity, request), True

    async def _linked(self, provider: str, subject: str) -> LinkedIdentity | None:
        return (
            await self.session.execute(
                select(LinkedIdentity).where(
                    LinkedIdentity.provider == provider, LinkedIdentity.subject == subject
                )
            )
        ).scalar_one_or_none()

    async def _link(self, user: User, identity: VerifiedIdentity, request: ProviderSignIn) -> None:
        """Link the provider to `user`, replacing an older account of the same provider."""
        for old in await self.identities(user):
            if old.provider == identity.provider:
                await self._revoke(old)
                await self.session.delete(old)
        await self.session.flush()
        refresh = None
        if identity.provider == "apple" and request.authorization_code:
            refresh = await self.apple_tokens.refresh_token_for(
                request.authorization_code, identity.client_id
            )
        self.session.add(
            LinkedIdentity(
                user_id=user.id,
                provider=identity.provider,
                subject=identity.subject,
                email=identity.email,
                refresh_token=encrypt_secret(refresh) if refresh else None,
                client_id=identity.client_id,
            )
        )
        await self.session.flush()

    async def _open(self, identity: VerifiedIdentity, request: ProviderSignIn) -> User:
        """A new account for a provider-confirmed address, with no password of its own."""
        if not request.accept_terms:
            raise RegistrationError(
                "Accept the terms and the privacy policy to open an account.",
                code=ProblemCode.TERMS_REQUIRED,
            )
        now = datetime.now(UTC)
        user = User(
            email=identity.email,
            first_name=(request.first_name or identity.given_name or identity.email.split("@")[0])[
                :50
            ],
            last_name=(request.last_name or identity.family_name or "")[:50],
            # Nobody knows this secret: the account signs in through the provider until a
            # reset link sets a password (F17.8.3).
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            password_set=False,
            email_confirmed_at=now,
            terms_accepted_at=now,
            terms_version=TERMS_VERSION,
        )
        self.users.add(user)
        await self.session.flush()
        ActivityService(self.session).record(user.id, ActivityKind.SIGNED_UP)
        await self._link(user, identity, request)
        return user

    async def identities(self, user: User) -> list[LinkedIdentity]:
        """The providers linked to `user`, oldest first."""
        return list(
            (
                await self.session.execute(
                    select(LinkedIdentity)
                    .where(LinkedIdentity.user_id == user.id)
                    .order_by(LinkedIdentity.created_at)
                )
            ).scalars()
        )

    async def unlink(self, user: User, provider: str) -> None:
        """Stop `provider` signing in to `user`; refused while it is the only way in.

        Raises NotFoundError when it is not linked, DomainError (last_way_in) when the
        account has no password and no other provider.
        """
        linked = await self.identities(user)
        target = next((i for i in linked if i.provider == provider), None)
        if target is None:
            raise NotFoundError("That provider is not linked.")
        if not user.password_set and len(linked) == 1:
            raise DomainError(
                "Add a password before unlinking the only way to sign in.",
                code=ProblemCode.LAST_WAY_IN,
            )
        await self._revoke(target)
        await self.session.delete(target)
        await self.session.flush()

    async def revoke_all(self, user: User) -> None:
        """Revoke every kept provider token, as the account is deleted (App Review 5.1.1)."""
        for identity in await self.identities(user):
            await self._revoke(identity)

    async def _revoke(self, identity: LinkedIdentity) -> None:
        if identity.provider != "apple" or not identity.refresh_token or not identity.client_id:
            return
        try:
            token = decrypt_secret(identity.refresh_token)
        except InvalidFernetToken:
            # Stored under a JWT key since rotated: the account still goes, Apple keeps it.
            logger.warning("An Apple token could not be read to revoke it")
            return
        await self.apple_tokens.revoke(token, identity.client_id)

    async def apple_notification(self, payload: str) -> None:
        """Act on Apple's server-to-server notification (F1.6.3).

        Consent withdrawn or the Apple ID deleted unlinks Apple from the account; the
        account itself stays, reachable by its password or another provider. Email
        forwarding switched on or off changes nothing here. Raises AuthenticationError
        (id_token_invalid) for a payload Apple did not sign.
        """
        try:
            events: dict[str, Any] = await self.verifier.apple_events(payload)
        except InvalidIdToken as err:
            raise AuthenticationError(
                "The notification could not be checked.", code=ProblemCode.ID_TOKEN_INVALID
            ) from err
        if events.get("type") not in {"consent-revoked", "account-delete"}:
            return
        linked = await self._linked("apple", str(events.get("sub")))
        if linked is not None:
            await self.session.delete(linked)
            await self.session.flush()
