import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import AuthenticationError, ProblemCode, RegistrationError
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_dummy_hash,
    get_password_hash,
    verify_password,
)
from app.domain.passwords import password_problems
from app.domain.terms import TERMS_VERSION
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repository.user import UserRepository
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from app.schemas.user import UserResponse
from app.services.account import EmailAddressGuard


class AuthService:
    """Business logic for authentication and registration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def _create_session(self, user_id: uuid.UUID) -> tuple[str, str]:
        """Helper to create access and refresh tokens, and persist the refresh token."""
        access_token = create_access_token(subject=user_id)
        refresh_token_str = create_refresh_token()
        family_id = uuid.uuid4()

        settings = get_settings()
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

        rt = RefreshToken(
            user_id=user_id,
            token=refresh_token_str,
            family_id=family_id,
            expires_at=expires_at,
        )
        self.session.add(rt)
        await self.session.flush()

        return access_token, refresh_token_str

    async def register(
        self, request: RegisterRequest, guard: EmailAddressGuard | None = None
    ) -> tuple[UserResponse, str, str]:
        """Open an account, unconfirmed until its owner follows the emailed link (F17.8.2).

        Refused (terms_required) unless the terms and privacy policy are accepted; which
        version, and when, is kept on the account (F17.9.4).

        `guard` refuses throwaway and undeliverable addresses with their own codes
        (F17.8.4); a taken address stays a generic refusal (G2).
        """
        problems = password_problems(request.password)
        if problems:
            raise RegistrationError(
                f"The password needs {', '.join(problems)}.", code=ProblemCode.WEAK_PASSWORD
            )
        if not request.accept_terms:
            raise RegistrationError(
                "Accept the terms and the privacy policy to open an account.",
                code=ProblemCode.TERMS_REQUIRED,
            )
        if guard is not None:
            await guard.check(request.email)

        existing_user = await self.repo.get_by_email(request.email)
        if existing_user:
            raise RegistrationError("Registration failed. Please check your details and try again.")

        hashed_password = get_password_hash(request.password)
        user = User(
            email=request.email,
            password_hash=hashed_password,
            first_name=request.first_name,
            last_name=request.last_name,
            terms_accepted_at=datetime.now(UTC),
            terms_version=TERMS_VERSION,
        )
        self.repo.add(user)
        try:
            await self.session.flush()
        except IntegrityError as err:
            await self.session.rollback()
            raise RegistrationError(
                "Registration failed. Please check your details and try again."
            ) from err

        access_token, refresh_token = await self._create_session(user.id)
        return UserResponse.model_validate(user), access_token, refresh_token

    async def login(self, request: LoginRequest) -> tuple[UserResponse, str, str]:
        user = await self.repo.get_by_email(request.email)

        if not user:
            verify_password(request.password, get_dummy_hash())
            raise AuthenticationError(
                "Invalid email or password.", code=ProblemCode.INVALID_CREDENTIALS
            )

        if not verify_password(request.password, user.password_hash):
            raise AuthenticationError(
                "Invalid email or password.", code=ProblemCode.INVALID_CREDENTIALS
            )

        access_token, refresh_token = await self._create_session(user.id)
        return UserResponse.model_validate(user), access_token, refresh_token

    async def refresh(self, request: RefreshRequest) -> tuple[UserResponse, str, str]:
        stmt = select(RefreshToken).where(RefreshToken.token == request.refresh_token)
        rt = (await self.session.execute(stmt)).scalar_one_or_none()

        if not rt:
            raise AuthenticationError("Invalid refresh token.")

        now = datetime.now(UTC)

        # Reuse detection
        if rt.is_used or rt.revoked_at or rt.expires_at < now:
            if rt.family_id:
                revoke_stmt = (
                    update(RefreshToken)
                    .where(RefreshToken.family_id == rt.family_id)
                    .values(revoked_at=now)
                )
                await self.session.execute(revoke_stmt)
                await self.session.flush()
            raise AuthenticationError(
                "Session expired. Please log in again.", code=ProblemCode.SESSION_EXPIRED
            )

        rt.is_used = True
        rt.revoked_at = now

        user_stmt = select(User).where(User.id == rt.user_id)
        user = (await self.session.execute(user_stmt)).scalar_one_or_none()
        if not user:
            raise AuthenticationError("User not found.")

        access_token = create_access_token(subject=user.id)
        new_refresh_token_str = create_refresh_token()

        new_rt = RefreshToken(
            user_id=user.id,
            token=new_refresh_token_str,
            family_id=rt.family_id,
            expires_at=await self._extended_expiry(rt.family_id, now),
        )
        self.session.add(new_rt)
        await self.session.flush()

        return UserResponse.model_validate(user), access_token, new_refresh_token_str

    async def _extended_expiry(self, family_id: uuid.UUID, now: datetime) -> datetime:
        """When a session refreshed now ends: a full term from now, within its absolute cap.

        Someone using the app keeps their session; one left alone ends after the term, and
        none outlives the cap counted from sign-in (F1.2.2).
        """
        settings = get_settings()
        signed_in = await self.session.scalar(
            select(func.min(RefreshToken.created_at)).where(RefreshToken.family_id == family_id)
        )
        cap = (signed_in or now) + timedelta(days=settings.refresh_token_absolute_days)
        return min(now + timedelta(days=settings.refresh_token_expire_days), cap)

    async def logout(self, request: RefreshRequest) -> None:
        stmt = select(RefreshToken).where(RefreshToken.token == request.refresh_token)
        rt = (await self.session.execute(stmt)).scalar_one_or_none()

        if rt and rt.family_id:
            now = datetime.now(UTC)
            revoke_stmt = (
                update(RefreshToken)
                .where(RefreshToken.family_id == rt.family_id)
                .values(revoked_at=now, is_used=True)
            )
            await self.session.execute(revoke_stmt)
            await self.session.flush()
