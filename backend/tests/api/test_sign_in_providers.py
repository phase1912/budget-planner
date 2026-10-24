"""Signing in with Google and Apple (F1.6): the real token checks against a key set the
tests publish themselves — forged, foreign and stale tokens refused — and accounts linked
only by their owner (BRD N2)."""

import hashlib
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.oidc import JwksIdTokenVerifier
from app.api.dependencies import get_apple_tokens, get_id_token_verifier
from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.session import get_db_session
from app.main import create_app
from app.models.linked_identity import LinkedIdentity
from app.models.user import User
from tests.factories.user import UserFactory

NONCE = "a-nonce-of-sixteen-or-more"
GOOGLE_WEB = "google-web-client"
APPLE_WEB = "app.budgetagent.web"
APPLE_APP = "app.budgetagent"

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_STRANGER = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_ISSUER = {"google": "https://accounts.google.com", "apple": "https://appleid.apple.com"}


def _key_set() -> dict[str, Any]:
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(_KEY.public_key(), as_dict=True)
    return {"keys": [{**jwk, "kid": "k1", "alg": "RS256", "use": "sig"}]}


async def _fetch(_url: str) -> dict[str, Any]:
    return _key_set()


def _token(
    provider: str = "google",
    sub: str = "subject-1",
    email: str = "ann@example.com",
    *,
    aud: str = GOOGLE_WEB,
    nonce: str = NONCE,
    verified: Any = True,
    key: rsa.RSAPrivateKey = _KEY,
    expires_in: int = 600,
    **extra: Any,
) -> str:
    now = int(time.time())
    claims = {
        "iss": _ISSUER[provider],
        "aud": aud,
        "sub": sub,
        "email": email,
        "email_verified": verified,
        "nonce": nonce,
        "iat": now,
        "exp": now + expires_in,
        **extra,
    }
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})


class _AppleTokens:
    """Apple's endpoints as a stub: every revoked token is noted."""

    configured = True

    def __init__(self) -> None:
        self.revoked: list[tuple[str, str]] = []

    async def refresh_token_for(self, authorization_code: str, client_id: str) -> str | None:
        return f"refresh-for-{authorization_code}"

    async def revoke(self, refresh_token: str, client_id: str) -> None:
        self.revoked.append((refresh_token, client_id))


@pytest.fixture
def providers_on() -> Iterator[None]:
    settings = get_settings()
    with (
        patch.object(settings, "google_client_ids", [GOOGLE_WEB]),
        patch.object(settings, "apple_client_ids", [APPLE_WEB, APPLE_APP]),
    ):
        yield


async def _call(
    session: AsyncSession,
    method: str,
    url: str,
    json: Any = None,
    *,
    as_user: User | None = None,
    apple: _AppleTokens | None = None,
) -> Response:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    settings = get_settings()
    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_id_token_verifier] = lambda: JwksIdTokenVerifier(
        {"google": settings.google_client_ids, "apple": settings.apple_client_ids}, _fetch
    )
    app.dependency_overrides[get_apple_tokens] = lambda: apple or _AppleTokens()
    headers = {}
    if as_user is not None:
        token = jwt.encode(
            {"sub": str(as_user.id)}, settings.jwt_secret_key.get_secret_value(), algorithm="HS256"
        )
        headers["Authorization"] = f"Bearer {token}"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as client:
        return await client.request(method, url, json=json)


def _sign_in(token: str, **extra: Any) -> dict[str, Any]:
    return {"id_token": token, "nonce": NONCE, **extra}


async def _identities(session: AsyncSession) -> list[tuple[str, str]]:
    rows = (await session.execute(select(LinkedIdentity))).scalars()
    return [(i.provider, i.subject) for i in rows]


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_a_new_address_opens_an_account_without_a_password(
    db_session: AsyncSession,
) -> None:
    response = await _call(
        db_session,
        "POST",
        "/auth/oidc/google",
        _sign_in(_token(given_name="Ann", family_name="Lee"), accept_terms=True),
    )

    body = response.json()
    assert response.status_code == 200, body
    assert (body["user"]["email"], body["user"]["first_name"]) == ("ann@example.com", "Ann")
    assert body["user"]["has_password"] is False
    assert body["user"]["email_confirmed"] is True
    assert await _identities(db_session) == [("google", "subject-1")]


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_the_same_provider_account_signs_in_to_the_same_account_again(
    db_session: AsyncSession,
) -> None:
    first = await _call(
        db_session, "POST", "/auth/oidc/google", _sign_in(_token(), accept_terms=True)
    )
    again = await _call(db_session, "POST", "/auth/oidc/google", _sign_in(_token()))

    assert again.status_code == 200
    assert again.json()["user"]["id"] == first.json()["user"]["id"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_a_new_account_needs_the_terms_accepted(db_session: AsyncSession) -> None:
    response = await _call(db_session, "POST", "/auth/oidc/google", _sign_in(_token()))

    assert (response.status_code, response.json()["code"]) == (400, "terms_required")
    assert await _identities(db_session) == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
@pytest.mark.parametrize(
    "token",
    [
        pytest.param(_token(key=_STRANGER), id="forged signature"),
        pytest.param(_token(aud="someone-elses-client"), id="another audience"),
        pytest.param(_token(nonce="another-sign-in-nonce"), id="another sign-in"),
        pytest.param(_token(expires_in=-3600), id="expired"),
        pytest.param(_token("apple", aud=GOOGLE_WEB), id="wrong issuer"),
    ],
)
async def test_a_token_not_issued_to_us_for_this_sign_in_is_refused(
    db_session: AsyncSession, token: str
) -> None:
    response = await _call(
        db_session, "POST", "/auth/oidc/google", _sign_in(token, accept_terms=True)
    )

    assert (response.status_code, response.json()["code"]) == (401, "id_token_invalid")
    assert await _identities(db_session) == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_an_address_the_provider_has_not_confirmed_opens_nothing(
    db_session: AsyncSession,
) -> None:
    response = await _call(
        db_session,
        "POST",
        "/auth/oidc/google",
        _sign_in(_token(verified=False), accept_terms=True),
    )

    assert (response.status_code, response.json()["code"]) == (401, "provider_email_unverified")


@pytest.mark.asyncio
async def test_a_provider_without_client_ids_is_off(db_session: AsyncSession) -> None:
    listed = await _call(db_session, "GET", "/auth/providers")
    response = await _call(
        db_session, "POST", "/auth/oidc/google", _sign_in(_token(), accept_terms=True)
    )

    assert listed.json() == {"google": None, "apple": None}
    assert (response.status_code, response.json()["code"]) == (404, "sign_in_provider_off")


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_the_web_learns_which_providers_are_on(db_session: AsyncSession) -> None:
    listed = await _call(db_session, "GET", "/auth/providers")

    assert listed.json() == {"google": GOOGLE_WEB, "apple": APPLE_WEB}


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_an_existing_account_is_linked_only_with_its_password(
    db_session: AsyncSession,
) -> None:
    owner = await UserFactory.create_async(
        email="ann@example.com", password_hash=get_password_hash("Correct-horse-1")
    )
    url = "/auth/oidc/google"

    asked = await _call(db_session, "POST", url, _sign_in(_token()))
    wrong = await _call(db_session, "POST", url, _sign_in(_token(), password="guess"))
    linked = await _call(db_session, "POST", url, _sign_in(_token(), password="Correct-horse-1"))

    assert (asked.status_code, asked.json()["code"]) == (409, "link_needs_password")
    assert wrong.status_code == 401
    assert linked.status_code == 200, linked.json()
    assert linked.json()["user"]["id"] == str(owner.id)
    assert await _identities(db_session) == [("google", "subject-1")]


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_another_users_provider_account_cannot_be_linked_to_mine(
    db_session: AsyncSession,
) -> None:
    await _call(db_session, "POST", "/auth/oidc/google", _sign_in(_token(), accept_terms=True))
    me = await UserFactory.create_async(email="me@example.com")

    response = await _call(db_session, "POST", "/auth/oidc/google", _sign_in(_token()), as_user=me)

    assert (response.status_code, response.json()["code"]) == (409, "identity_taken")


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_signed_in_the_provider_is_linked_to_my_account(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async(email="me@example.com")

    response = await _call(
        db_session,
        "POST",
        "/auth/oidc/google",
        _sign_in(_token(email="other-address@gmail.com")),
        as_user=me,
    )
    listed = await _call(db_session, "GET", "/users/me/identities", as_user=me)

    assert response.json()["user"]["id"] == str(me.id)
    assert [(i["provider"], i["email"]) for i in listed.json()] == [
        ("google", "other-address@gmail.com")
    ]


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_apples_native_sign_in_sends_the_nonce_hashed(db_session: AsyncSession) -> None:
    hashed = hashlib.sha256(NONCE.encode()).hexdigest()
    token = _token("apple", aud=APPLE_APP, nonce=hashed, verified="true")

    response = await _call(
        db_session,
        "POST",
        "/auth/oidc/apple",
        _sign_in(token, accept_terms=True, first_name="Ann", authorization_code="c1"),
    )

    assert response.status_code == 200, response.json()
    assert response.json()["user"]["first_name"] == "Ann"


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_the_only_way_in_cannot_be_unlinked(db_session: AsyncSession) -> None:
    opened = await _call(
        db_session, "POST", "/auth/oidc/google", _sign_in(_token(), accept_terms=True)
    )
    me = await db_session.get(User, opened.json()["user"]["id"])
    assert me is not None

    refused = await _call(db_session, "DELETE", "/users/me/identities/google", as_user=me)
    me.password_set = True
    unlinked = await _call(db_session, "DELETE", "/users/me/identities/google", as_user=me)

    assert (refused.status_code, refused.json()["code"]) == (409, "last_way_in")
    assert unlinked.status_code == 204
    assert await _identities(db_session) == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_an_account_without_a_password_is_deleted_by_its_address_and_apple_revoked(
    db_session: AsyncSession,
) -> None:
    apple = _AppleTokens()
    token = _token("apple", aud=APPLE_APP, email="x@privaterelay.appleid.com")
    opened = await _call(
        db_session,
        "POST",
        "/auth/oidc/apple",
        _sign_in(token, accept_terms=True, authorization_code="c1"),
        apple=apple,
    )
    me = await db_session.get(User, opened.json()["user"]["id"])
    assert me is not None

    wrong = await _call(
        db_session, "DELETE", "/users/me", {"password": "nope"}, as_user=me, apple=apple
    )
    deleted = await _call(
        db_session,
        "DELETE",
        "/users/me",
        {"password": "X@privaterelay.appleid.com"},
        as_user=me,
        apple=apple,
    )

    assert wrong.status_code == 403
    assert deleted.status_code == 204
    assert apple.revoked == [("refresh-for-c1", APPLE_APP)]


@pytest.mark.asyncio
@pytest.mark.usefixtures("providers_on")
async def test_apple_withdrawing_consent_unlinks_apple(db_session: AsyncSession) -> None:
    token = _token("apple", aud=APPLE_APP)
    await _call(db_session, "POST", "/auth/oidc/apple", _sign_in(token, accept_terms=True))
    now = int(time.time())
    notice = jwt.encode(
        {
            "iss": _ISSUER["apple"],
            "aud": APPLE_APP,
            "sub": "subject-1",
            "iat": now,
            "exp": now + 600,
            "events": '{"type": "consent-revoked", "sub": "subject-1"}',
        },
        _KEY,
        algorithm="RS256",
        headers={"kid": "k1"},
    )
    forged = jwt.encode(
        {"iss": _ISSUER["apple"], "aud": APPLE_APP, "sub": "s", "iat": now, "exp": now + 600},
        _STRANGER,
        algorithm="RS256",
        headers={"kid": "k1"},
    )

    refused = await _call(db_session, "POST", "/auth/apple/notifications", {"payload": forged})
    accepted = await _call(db_session, "POST", "/auth/apple/notifications", {"payload": notice})

    assert refused.status_code == 401
    assert accepted.status_code == 204
    assert await _identities(db_session) == []


@pytest.mark.asyncio
async def test_apples_web_answer_goes_back_to_the_client_in_the_fragment(
    db_session: AsyncSession,
) -> None:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/apple/callback",
            data={
                "state": "s1",
                "id_token": "t",
                "code": "c",
                "user": '{"name": {"firstName": "Ann", "lastName": "Lee"}}',
            },
        )

    location = response.headers["location"]
    assert response.status_code == 303
    assert location.endswith(
        "/auth/callback/apple#state=s1&id_token=t&code=c&first_name=Ann&last_name=Lee"
    )
