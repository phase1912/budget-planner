from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import AuthenticationError, RegistrationError
from app.core.security import (
    create_access_token,
    get_dummy_hash,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.repository.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserResponse


class AuthService:
    """Business logic for authentication and registration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def register(self, request: RegisterRequest) -> tuple[UserResponse, str]:
        # Simple check for common passwords
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

        token = create_access_token(subject=user.id)
        return UserResponse.model_validate(user), token

    async def login(self, request: LoginRequest) -> tuple[UserResponse, str]:
        user = await self.repo.get_by_email(request.email)

        if not user:
            # Mitigate timing attack
            verify_password(request.password, get_dummy_hash())
            raise AuthenticationError("Invalid email or password.")

        if not verify_password(request.password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        token = create_access_token(subject=user.id)
        return UserResponse.model_validate(user), token
