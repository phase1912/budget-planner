from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import Language, UserResponse


class RegisterRequest(BaseModel):
    """Payload for registering a new account (F1.1.3)."""

    email: EmailStr
    password: str
    first_name: str
    last_name: str
    # The language the sign-up screen was in: the confirmation letter is written in it.
    language: Language | None = None
    # Ticked "I accept the terms and the privacy policy" (F17.9.4); required to be true.
    accept_terms: bool = False


class LoginRequest(BaseModel):
    """Payload for authenticating with password (F1.1.4)."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response containing the authenticated user and their access token."""

    user: UserResponse
    access_token: str
    refresh_token: str


class SecondFactorChallenge(BaseModel):
    """The password was right; the account wants its authenticator code too (F18.6.1)."""

    second_factor_required: Literal[True] = True
    second_factor_token: str


class SecondFactorRequest(BaseModel):
    """The challenge from sign-in and a code from the app, or a recovery code."""

    token: str
    code: str = Field(min_length=6, max_length=16)


class RefreshRequest(BaseModel):
    """Payload for refreshing an access token (F1.2.3)."""

    refresh_token: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class LinkRequest(BaseModel):
    """The token a link from a letter carries (F17.8)."""

    token: str


class ForgotPasswordRequest(BaseModel):
    """Payload for asking for a password reset letter (F17.8.3)."""

    email: EmailStr
    language: Language | None = None


class ResetPasswordRequest(BaseModel):
    """Payload for setting a new password from a reset link (F17.8.3)."""

    token: str
    password: str


class ProviderSignInRequest(BaseModel):
    """What the client sends after Google's or Apple's sign-in (F1.6.1).

    `password` links an existing account with the same address; `accept_terms` opens a
    new one. Apple gives the name to the client once, on the first sign-in, so the client
    passes it on; `authorization_code` lets the server revoke Apple's tokens later.
    """

    id_token: str = Field(min_length=1, max_length=8192)
    nonce: str = Field(min_length=16, max_length=256)
    password: str | None = None
    accept_terms: bool = False
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)
    authorization_code: str | None = Field(default=None, max_length=1024)


class SignInProviders(BaseModel):
    """The client id the web opens each provider with; null hides its button (F1.6.2)."""

    google: str | None
    apple: str | None


class AppleNotification(BaseModel):
    """One of Apple's server-to-server notifications: a JWT Apple signed (F1.6.3)."""

    payload: str = Field(min_length=1, max_length=8192)


class LinkedIdentityRead(BaseModel):
    """A provider that signs in to the account, as Settings lists it (F1.6.2)."""

    provider: Literal["google", "apple"]
    email: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
