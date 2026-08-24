import uuid

import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings
from app.core.context import current_user_id


class UserContextMiddleware(BaseHTTPMiddleware):
    """Extracts user ID from JWT and sets it in a ContextVar for the repository layer."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        auth_header = request.headers.get("Authorization")
        user_id = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer ") :]
            settings = get_settings()
            try:
                payload = jwt.decode(
                    token, settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"]
                )
                sub = payload.get("sub")
                if sub:
                    user_id = uuid.UUID(sub)
            except Exception:
                pass

        token_ctx = current_user_id.set(user_id)
        try:
            response = await call_next(request)
        finally:
            current_user_id.reset(token_ctx)

        return response
