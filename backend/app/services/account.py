"""Proving an account's address, and the links that change its password or address (F17.8)."""

import uuid
from collections.abc import Collection
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import (
    EmailRefusedError,
    InvalidLinkError,
    PermissionDeniedError,
    ProblemCode,
    RegistrationError,
)
from app.core.config import get_settings
from app.core.security import (
    create_link_token,
    fingerprint,
    get_password_hash,
    read_link_token,
    verify_password,
)
from app.domain.activity import ActivityKind
from app.domain.email_addresses import disposable_domains, domain_of, is_disposable
from app.domain.letters import LetterKind, write_letter
from app.domain.passwords import password_problems
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.ports.email import Letter
from app.ports.mail_domains import MailDomainResolverPort
from app.repository.user import UserRepository
from app.schemas.user import UserResponse
from app.services.activity import ActivityService

CONFIRM_LINK_LIFETIME = timedelta(hours=24)
RESET_LINK_LIFETIME = timedelta(hours=1)

_CONFIRM = "confirm_email"
_RESET = "reset_password"
_CHANGE = "change_email"


class EmailAddressGuard:
    """Refuses addresses an account cannot be trusted with (F17.8.4).

    Throwaway domains are refused from the list kept in the repository, and domains DNS
    says receive no mail at all. Nothing about the address leaves the service but the
    domain's DNS lookup; when DNS cannot be asked, the address is let through.
    """

    def __init__(
        self,
        resolver: MailDomainResolverPort | None,
        blocklist: Collection[str] | None = None,
    ) -> None:
        self.resolver = resolver
        self.blocklist = disposable_domains() if blocklist is None else blocklist

    async def check(self, email: str) -> None:
        """Raise EmailRefusedError, with its own code for each reason, or return."""
        domain = domain_of(email)
        if is_disposable(domain, self.blocklist):
            raise EmailRefusedError(
                "Addresses from throwaway mail services cannot open an account.",
                code=ProblemCode.DISPOSABLE_EMAIL,
                params={"domain": domain},
            )
        if self.resolver is not None and await self.resolver.receives_mail(domain) is False:
            raise EmailRefusedError(
                f"No mail can be delivered to {domain}: check the address for a typo.",
                code=ProblemCode.EMAIL_DOMAIN_UNREACHABLE,
                params={"domain": domain},
            )


def _link(path: str, token: str) -> str:
    return f"{get_settings().link_base}/{path}?{urlencode({'token': token})}"


class AccountService:
    """The account's address and password, changed only through links sent to it (F17.8).

    Every link is a signed token bound to the state it changes — the address it was sent
    to, a fingerprint of the password — so it works once and stops when that state moves
    on. Methods that write a letter return it; the caller hands it to the Mailer, so
    sending never fails the request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def confirmation_letter_for(
        self, user_id: uuid.UUID, language: str | None = None
    ) -> Letter | None:
        """The confirmation letter for an account still unconfirmed, else None."""
        user = await self.users.get(user_id)
        if user is None or user.email_confirmed:
            return None
        return self.confirmation_letter(user, language)

    def confirmation_letter(self, user: User, language: str | None = None) -> Letter:
        """The letter whose link proves `user` reads their address, valid 24 hours."""
        token = create_link_token(_CONFIRM, str(user.id), CONFIRM_LINK_LIFETIME, email=user.email)
        wording = write_letter(
            LetterKind.CONFIRM_EMAIL,
            user.language or language,
            name=user.first_name,
            link=_link("confirm-email", token),
        )
        return Letter(user.email, wording.subject, wording.body)

    async def confirm_email(self, token: str) -> User:
        """Mark the address the link was sent to as confirmed.

        Raises InvalidLinkError when the link expired, is not a confirmation link, or the
        account has moved to another address since. A second use changes nothing.
        """
        user, claims = await self._verified(token, _CONFIRM)
        if user.email != claims.get("email"):
            raise InvalidLinkError("This link was sent to an address the account no longer uses.")
        if user.email_confirmed_at is None:
            user.email_confirmed_at = datetime.now(UTC)
            ActivityService(self.session).record(user.id, ActivityKind.EMAIL_CONFIRMED)
            await self.session.flush()
        return user

    async def forgot_password(self, email: str, language: str | None) -> Letter | None:
        """The reset letter for the account with this address, or None for none.

        The caller answers the same either way, so the form never tells whether an
        address has an account (G2). The link works one hour, and once: setting a
        password changes the fingerprint it carries.
        """
        user = await self.users.get_by_email(email)
        if user is None:
            return None
        token = create_link_token(
            _RESET, str(user.id), RESET_LINK_LIFETIME, pwd=fingerprint(user.password_hash)
        )
        wording = write_letter(
            LetterKind.RESET_PASSWORD,
            user.language or language,
            name=user.first_name,
            link=_link("reset-password", token),
        )
        return Letter(user.email, wording.subject, wording.body)

    async def reset_password(self, token: str, password: str) -> None:
        """Set a new password from a reset link and end every session of the account.

        Following the link proves the address too, so an unconfirmed one becomes
        confirmed. Raises InvalidLinkError for a used or expired link, and
        RegistrationError (weak_password) for a password the rules refuse.
        """
        user, claims = await self._verified(token, _RESET)
        if fingerprint(user.password_hash) != claims.get("pwd"):
            raise InvalidLinkError("This link has already been used.")
        problems = password_problems(password)
        if problems:
            raise RegistrationError(
                f"The password needs {', '.join(problems)}.", code=ProblemCode.WEAK_PASSWORD
            )
        now = datetime.now(UTC)
        user.password_hash = get_password_hash(password)
        user.password_set = True
        user.email_confirmed_at = user.email_confirmed_at or now
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.session.flush()

    async def request_email_change(
        self, user: User, new_email: str, password: str, guard: EmailAddressGuard
    ) -> Letter:
        """The letter to `new_email` whose link switches the account to it.

        Asks for the password, so an unattended signed-in screen cannot hand the account
        away. Raises PermissionDeniedError for a wrong password, EmailRefusedError for an
        address in use or one sign-up would refuse.
        """
        if not verify_password(password, user.password_hash):
            raise PermissionDeniedError(
                "The password is not right.", code=ProblemCode.INVALID_CREDENTIALS
            )
        if new_email.lower() == user.email.lower() or await self.users.get_by_email(new_email):
            raise EmailRefusedError(
                "This address cannot be used for the account.", code=ProblemCode.EMAIL_TAKEN
            )
        await guard.check(new_email)
        token = create_link_token(
            _CHANGE, str(user.id), CONFIRM_LINK_LIFETIME, email=new_email, old=user.email
        )
        wording = write_letter(
            LetterKind.CHANGE_EMAIL,
            user.language,
            name=user.first_name,
            link=_link("confirm-email-change", token),
        )
        return Letter(new_email, wording.subject, wording.body)

    async def confirm_email_change(self, token: str) -> tuple[User, Letter]:
        """Switch the account to the address the link was sent to; returns the notice.

        The notice goes to the old address, so a change its owner did not make does not
        go unseen. Raises InvalidLinkError for a used or expired link, EmailRefusedError
        when another account took the address meanwhile.
        """
        user, claims = await self._verified(token, _CHANGE)
        old = user.email
        new_email = str(claims.get("email", ""))
        if old != claims.get("old") or not new_email:
            raise InvalidLinkError("This link has already been used.")
        if await self.users.get_by_email(new_email):
            raise EmailRefusedError(
                "This address cannot be used for the account.", code=ProblemCode.EMAIL_TAKEN
            )
        user.email = new_email
        user.email_confirmed_at = datetime.now(UTC)
        await self.session.flush()
        wording = write_letter(
            LetterKind.EMAIL_CHANGED, user.language, name=user.first_name, email=new_email
        )
        return user, Letter(old, wording.subject, wording.body)

    async def _verified(self, token: str, purpose: str) -> tuple[User, dict[str, Any]]:
        """The account a valid link of this purpose belongs to, and the link's claims."""
        claims = read_link_token(token, purpose)
        user = None
        if claims is not None:
            try:
                user = await self.users.get(uuid.UUID(str(claims.get("sub"))))
            except ValueError:
                user = None
        if user is None or claims is None:
            raise InvalidLinkError("This link has expired or is not valid.")
        return user, claims


def admin_sign_in_letter(user: UserResponse, when: datetime) -> Letter:
    """The letter telling an admin their account was signed in to (F18.6.1)."""
    wording = write_letter(
        LetterKind.ADMIN_SIGN_IN,
        user.language,
        name=user.first_name,
        when=f"{when:%Y-%m-%d %H:%M}",
    )
    return Letter(str(user.email), wording.subject, wording.body)
