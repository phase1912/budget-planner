import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import AuthenticationError, RegistrationError
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_dummy_hash,
    get_password_hash,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repository.user import UserRepository
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest
from app.schemas.user import UserResponse


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

    async def register(self, request: RegisterRequest) -> tuple[UserResponse, str, str]:
        common_passwords = {"password", "12345678", "qwertyui", "admin123", "password123"}
        if request.password.lower() in common_passwords or len(request.password) < 8:
            raise RegistrationError("Registration failed. Please check your details and try again.")

        existing_user = await self.repo.get_by_email(request.email)
        if existing_user:
            raise RegistrationError("Registration failed. Please check your details and try again.")

        hashed_password = get_password_hash(request.password)
        user = User(
            email=request.email,
            password_hash=hashed_password,
            first_name=request.first_name,
            last_name=request.last_name,
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
            raise AuthenticationError("Invalid email or password.")

        if not verify_password(request.password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

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
            raise AuthenticationError("Session expired. Please log in again.")

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
            expires_at=rt.expires_at,
        )
        self.session.add(new_rt)
        await self.session.flush()

        return UserResponse.model_validate(user), access_token, new_refresh_token_str

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
