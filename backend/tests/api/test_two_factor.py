"""Two-factor sign-in, optional for anyone and required for admins (F18.6.1, G4)."""

from collections.abc import AsyncIterator
from typing import Any

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_mailer
from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash
from app.db.session import get_db_session
from app.main import create_app
from app.models.user import User
from tests.factories.user import UserFactory

PASSWORD = "Correct-Horse-42"


class Outbox:
    def __init__(self) -> None:
        self.letters: list[Any] = []

    async def deliver(self, letter: Any) -> bool:
        self.letters.append(letter)
        return True


async def _call(
    session: AsyncSession,
    method: str,
    url: str,
    *,
    json: Any = None,
    token: str | None = None,
    outbox: Outbox | None = None,
) -> Response:
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    app.dependency_overrides[get_mailer] = lambda: outbox or Outbox()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as client:
        return await client.request(method, url, json=json)


async def _turn_on(session: AsyncSession, user: User) -> tuple[str, list[str]]:
    token = create_access_token(user.id)
    setup = await _call(session, "POST", "/users/me/two-factor/setup", token=token)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["qr_svg"].startswith("<svg") or "<svg" in setup.json()["qr_svg"]
    confirmed = await _call(
        session,
        "POST",
        "/users/me/two-factor/confirm",
        json={"code": pyotp.TOTP(secret).now()},
        token=token,
    )
    assert confirmed.status_code == 200
    return secret, confirmed.json()["recovery_codes"]


async def _sign_in(session: AsyncSession, email: str) -> Response:
    return await _call(session, "POST", "/auth/login", json={"email": email, "password": PASSWORD})


@pytest.mark.asyncio
async def test_with_two_factor_on_the_password_alone_only_starts_a_sign_in(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(password_hash=get_password_hash(PASSWORD))
    secret, codes = await _turn_on(db_session, user)
    assert len(codes) == 10

    first = await _sign_in(db_session, user.email)
    assert first.status_code == 200
    assert first.json()["second_factor_required"] is True
    assert "access_token" not in first.json()

    challenge = first.json()["second_factor_token"]
    # The challenge is not a session.
    refused = await _call(db_session, "GET", "/users/me", token=challenge)
    assert refused.status_code == 401

    done = await _call(
        db_session,
        "POST",
        "/auth/login/second-factor",
        json={"token": challenge, "code": pyotp.TOTP(secret).now()},
    )
    assert done.status_code == 200
    me = await _call(db_session, "GET", "/users/me", token=done.json()["access_token"])
    assert me.json()["two_factor_enabled"] is True


@pytest.mark.asyncio
async def test_a_wrong_code_does_not_sign_in_and_a_recovery_code_works_once(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(password_hash=get_password_hash(PASSWORD))
    _, codes = await _turn_on(db_session, user)

    challenge = (await _sign_in(db_session, user.email)).json()["second_factor_token"]
    wrong = await _call(
        db_session,
        "POST",
        "/auth/login/second-factor",
        json={"token": challenge, "code": "000000"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["code"] == "two_factor_code_wrong"

    used = await _call(
        db_session,
        "POST",
        "/auth/login/second-factor",
        json={"token": challenge, "code": codes[0]},
    )
    assert used.status_code == 200
    again = await _call(
        db_session,
        "POST",
        "/auth/login/second-factor",
        json={"token": challenge, "code": codes[0]},
    )
    assert again.status_code == 401


@pytest.mark.asyncio
async def test_turning_it_off_needs_the_password_and_a_code(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async(password_hash=get_password_hash(PASSWORD))
    secret, _ = await _turn_on(db_session, user)
    token = create_access_token(user.id)

    no = await _call(
        db_session,
        "POST",
        "/users/me/two-factor/disable",
        json={"password": "Wrong-Horse-42", "code": pyotp.TOTP(secret).now()},
        token=token,
    )
    assert no.status_code in (401, 403)
    yes = await _call(
        db_session,
        "POST",
        "/users/me/two-factor/disable",
        json={"password": PASSWORD, "code": pyotp.TOTP(secret).now()},
        token=token,
    )
    assert yes.status_code == 204
    assert (await _sign_in(db_session, user.email)).json().get("access_token")


@pytest.mark.asyncio
async def test_an_admin_signed_in_with_the_password_alone_cannot_open_admin_pages(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "admin_second_factor_required", True)
    admin = await UserFactory.create_async(role="admin")

    plain = await _call(
        db_session, "GET", "/api/v1/admin/users", token=create_access_token(admin.id)
    )
    assert plain.status_code == 403
    assert plain.json()["code"] == "second_factor_required"

    strong = create_access_token(admin.id, second_factor=True)
    assert (await _call(db_session, "GET", "/api/v1/admin/users", token=strong)).status_code == 200


@pytest.mark.asyncio
async def test_a_refreshed_session_keeps_its_second_factor(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "admin_second_factor_required", True)
    admin = await UserFactory.create_async(role="admin", password_hash=get_password_hash(PASSWORD))
    secret, _ = await _turn_on(db_session, admin)
    challenge = (await _sign_in(db_session, admin.email)).json()["second_factor_token"]
    outbox = Outbox()
    session = (
        await _call(
            db_session,
            "POST",
            "/auth/login/second-factor",
            json={"token": challenge, "code": pyotp.TOTP(secret).now()},
            outbox=outbox,
        )
    ).json()
    assert len(outbox.letters) == 1  # an admin is told of every sign-in

    refreshed = await _call(
        db_session, "POST", "/auth/refresh", json={"refresh_token": session["refresh_token"]}
    )
    token = refreshed.json()["access_token"]
    assert (await _call(db_session, "GET", "/api/v1/admin/users", token=token)).status_code == 200
