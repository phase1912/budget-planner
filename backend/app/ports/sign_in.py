"""Ports for signing in with Google and Apple (F1.6, ADR-0035)."""

from dataclasses import dataclass
from typing import Any, Literal, Protocol

Provider = Literal["google", "apple"]
PROVIDERS: tuple[Provider, ...] = ("google", "apple")


class InvalidIdToken(Exception):
    """The token is not one the provider signed for this service, now, for this sign-in."""


@dataclass(frozen=True)
class VerifiedIdentity:
    """Who the provider vouches for: its stable subject and the address it holds.

    `client_id` is which of our client ids the token was issued to (the web's or an app's).
    `given_name` and `family_name` come from Google's token; Apple sends the name to the
    client once, on the first sign-in, never in the token.
    """

    provider: Provider
    subject: str
    email: str
    email_verified: bool
    client_id: str
    given_name: str | None = None
    family_name: str | None = None


class IdTokenVerifierPort(Protocol):
    """Checks a provider's signed tokens against its published keys and our client ids."""

    async def verify(self, provider: Provider, id_token: str, nonce: str) -> VerifiedIdentity:
        """The identity in an ID token issued to us for this `nonce` (F1.6.1).

        Raises InvalidIdToken for a bad signature, another audience or issuer, an expired
        token or a nonce that does not match.
        """
        ...

    async def apple_events(self, payload: str) -> dict[str, Any]:
        """The event in one of Apple's server-to-server notifications (F1.6.3).

        Raises InvalidIdToken for a payload Apple did not sign for this service.
        """
        ...


class AppleTokensPort(Protocol):
    """Apple's token endpoints, behind the client secret only the server holds (F1.6.3)."""

    @property
    def configured(self) -> bool:
        """Whether the key to sign the client secret is set; without it nothing is kept."""
        ...

    async def refresh_token_for(self, authorization_code: str, client_id: str) -> str | None:
        """Exchange a sign-in's authorization code for the refresh token to revoke later."""
        ...

    async def revoke(self, refresh_token: str, client_id: str) -> None:
        """Tell Apple the account is gone, so the app is removed from the user's Apple ID."""
        ...
