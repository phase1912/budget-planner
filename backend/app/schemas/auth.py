from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    """Payload for registering a new account (F1.1.3)."""

    email: EmailStr
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    """Payload for authenticating with password (F1.1.4)."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response containing the authenticated user and their access token."""

    user: UserResponse
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    """Payload for refreshing an access token (F1.2.3)."""

    refresh_token: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
