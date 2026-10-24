"""Google's and Apple's ID tokens, and Apple's token endpoints (F1.6, ADR-0035)."""

import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

import httpx
import jwt

from app.ports.sign_in import InvalidIdToken, Provider, VerifiedIdentity

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0)
_KEYS_KEPT = 3600.0
"""Seconds a provider's key set is reused; a token signed with a newer key refetches it."""

ISSUERS: Mapping[Provider, tuple[str, ...]] = {
    "google": ("https://accounts.google.com", "accounts.google.com"),
    "apple": ("https://appleid.apple.com",),
}
KEY_SETS: Mapping[Provider, str] = {
    "google": "https://www.googleapis.com/oauth2/v3/certs",
    "apple": "https://appleid.apple.com/auth/keys",
}
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_REVOKE_URL = "https://appleid.apple.com/auth/revoke"

FetchJson = Callable[[str], Awaitable[dict[str, Any]]]


async def _fetch_json(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(url)
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        return body


def _truthy(value: object) -> bool:
    """Apple writes `email_verified` as the string "true", Google as a boolean."""
    return value is True or value == "true"


class JwksIdTokenVerifier:
    """Verifies RS256 tokens with the key set each provider publishes.

    `audiences` are our client ids per provider; a provider with none is switched off
    and every token for it is refused. `fetch_json` is injectable so tests sign tokens
    with their own key set and the real checks run without the network.
    """

    def __init__(
        self,
        audiences: Mapping[Provider, Sequence[str]],
        fetch_json: FetchJson = _fetch_json,
    ) -> None:
        self.audiences = audiences
        self.fetch_json = fetch_json
        self._keys: dict[Provider, tuple[float, jwt.PyJWKSet]] = {}

    async def _key(self, provider: Provider, token: str) -> jwt.PyJWK:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
        except jwt.PyJWTError as err:
            raise InvalidIdToken("Not a signed token.") from err
        for fresh in (False, True):
            kept = self._keys.get(provider)
            if fresh or kept is None or time.monotonic() - kept[0] > _KEYS_KEPT:
                try:
                    keys = jwt.PyJWKSet.from_dict(await self.fetch_json(KEY_SETS[provider]))
                except (httpx.HTTPError, jwt.PyJWTError) as err:
                    raise InvalidIdToken("The provider's keys could not be read.") from err
                kept = (time.monotonic(), keys)
                self._keys[provider] = kept
            match = next((k for k in kept[1].keys if k.key_id == kid), None)
            if match is not None:
                return match
        raise InvalidIdToken("Signed with a key the provider does not publish.")

    async def _claims(self, provider: Provider, token: str) -> dict[str, Any]:
        audiences = list(self.audiences.get(provider, ()))
        if not audiences:
            raise InvalidIdToken("This provider is switched off.")
        key = await self._key(provider, token)
        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                key=key.key,
                algorithms=["RS256"],
                audience=audiences,
                issuer=list(ISSUERS[provider]),
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
                leeway=60,
            )
        except jwt.PyJWTError as err:
            raise InvalidIdToken(str(err)) from err
        return claims

    async def verify(self, provider: Provider, id_token: str, nonce: str) -> VerifiedIdentity:
        """The identity in `id_token`, once signature, audience, issuer, expiry and nonce hold.

        Apple's native sign-in sends the nonce's SHA-256 to Apple, so for Apple either the
        nonce or its hash matches.
        """
        claims = await self._claims(provider, id_token)
        expected = {nonce}
        if provider == "apple":
            expected.add(hashlib.sha256(nonce.encode()).hexdigest())
        if not nonce or claims.get("nonce") not in expected:
            raise InvalidIdToken("The token was not asked for by this sign-in.")
        email = claims.get("email")
        if not isinstance(email, str) or not email:
            raise InvalidIdToken("The token carries no email address.")
        return VerifiedIdentity(
            provider=provider,
            subject=str(claims["sub"]),
            email=email.lower(),
            email_verified=_truthy(claims.get("email_verified")),
            client_id=str(claims["aud"]),
            given_name=claims.get("given_name"),
            family_name=claims.get("family_name"),
        )

    async def apple_events(self, payload: str) -> dict[str, Any]:
        """The `events` of Apple's notification, after the same checks as an ID token."""
        claims = await self._claims("apple", payload)
        events = claims.get("events")
        if isinstance(events, str):
            events = json.loads(events)
        if not isinstance(events, dict):
            raise InvalidIdToken("The notification carries no event.")
        return events


class AppleTokens:
    """Apple's token and revoke endpoints, signed with a client secret made on each call.

    The client secret is a short-lived ES256 JWT from the Sign in with Apple key, so
    nothing long-lived is stored and no rotation is due (F1.6.3).
    """

    def __init__(
        self,
        team_id: str | None,
        key_id: str | None,
        private_key: str | None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.team_id = team_id
        self.key_id = key_id
        self.private_key = private_key
        self.transport = transport

    @property
    def configured(self) -> bool:
        """Whether the team, the key id and the key are all set."""
        return bool(self.team_id and self.key_id and self.private_key)

    def _client_secret(self, client_id: str) -> str:
        now = int(time.time())
        return jwt.encode(
            {
                "iss": self.team_id,
                "iat": now,
                "exp": now + 300,
                "aud": "https://appleid.apple.com",
                "sub": client_id,
            },
            str(self.private_key),
            algorithm="ES256",
            headers={"kid": self.key_id},
        )

    async def _post(self, url: str, data: dict[str, str]) -> httpx.Response:
        async with httpx.AsyncClient(timeout=_TIMEOUT, transport=self.transport) as client:
            return await client.post(url, data=data)

    async def refresh_token_for(self, authorization_code: str, client_id: str) -> str | None:
        """The refresh token for a sign-in's code, or None when Apple refuses or is off."""
        if not self.configured:
            return None
        try:
            response = await self._post(
                APPLE_TOKEN_URL,
                {
                    "client_id": client_id,
                    "client_secret": self._client_secret(client_id),
                    "code": authorization_code,
                    "grant_type": "authorization_code",
                },
            )
        except httpx.HTTPError:
            logger.warning("Apple's token endpoint could not be reached")
            return None
        if response.status_code != 200:
            logger.warning("Apple refused a sign-in's code: %s", response.status_code)
            return None
        token = response.json().get("refresh_token")
        return token if isinstance(token, str) else None

    async def revoke(self, refresh_token: str, client_id: str) -> None:
        """Revoke at Apple; a failure is logged, since the account goes either way."""
        if not self.configured:
            return
        try:
            response = await self._post(
                APPLE_REVOKE_URL,
                {
                    "client_id": client_id,
                    "client_secret": self._client_secret(client_id),
                    "token": refresh_token,
                    "token_type_hint": "refresh_token",
                },
            )
        except httpx.HTTPError:
            logger.warning("Apple's revoke endpoint could not be reached")
            return
        if response.status_code != 200:
            logger.warning("Apple refused to revoke a token: %s", response.status_code)
