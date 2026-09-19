import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import AuthenticationError
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.ports.storage import StoragePort
from app.services.storage import S3StorageService

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
        if user_id_str is None:
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

    return user


async def get_storage_service() -> AsyncGenerator[StoragePort, None]:
    """Dependency providing a StoragePort implementation."""
    settings = get_settings()
    async with S3StorageService(settings) as service:
        yield service
