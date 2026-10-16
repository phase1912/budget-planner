"""Accounts that belong to a real address its owner reads (F17.8, BRD N2)."""

import re
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_mail_domain_resolver, get_mailer
from app.core.security import create_access_token, create_link_token
from app.db.session import get_db_session
from app.main import create_app
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.ports.email import Letter
from tests.factories.user import UserFactory

PASSWORD = "Correct-Horse-42"


class RecordingMailer:
    """Keeps every letter instead of sending it."""

    def __init__(self) -> None:
        self.letters: list[Letter] = []

    async def deliver(self, letter: Letter) -> bool:
        self.letters.append(letter)
        return True


class NoMailDomains:
    """DNS that says no domain receives mail."""

    async def receives_mail(self, domain: str) -> bool | None:
        return False


async def _call(
    session: AsyncSession,
    method: str,
    url: str,
    *,
    json: Any = None,
    user: User | None = None,
    token: str | None = None,
    mailer: RecordingMailer | None = None,
    dns: Any = None,
) -> Response:
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    app.dependency_overrides[get_mailer] = lambda: mailer or RecordingMailer()
    app.dependency_overrides[get_mail_domain_resolver] = lambda: dns
    bearer = token or (create_access_token(user.id) if user else None)
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as client:
        return await client.request(method, url, json=json)


def _token_in(letter: Letter) -> str:
    match = re.search(r"token=([\w.\-]+)", letter.body)
    assert match, letter.body
    return match.group(1)


async def _sign_up(session: AsyncSession, email: str, mailer: RecordingMailer) -> Response:
    return await _call(
        session,
        "POST",
        "/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "first_name": "Ann",
            "last_name": "Lee",
            "language": "pl",
        },
        mailer=mailer,
    )


@pytest.mark.asyncio
async def test_sign_up_sends_a_link_that_confirms_the_address(db_session: AsyncSession) -> None:
    mailer = RecordingMailer()

    signed_up = await _sign_up(db_session, "ann@example.com", mailer)

    assert signed_up.status_code == 201
    assert signed_up.json()["user"]["email_confirmed"] is False
    [letter] = mailer.letters
    assert (letter.to, letter.subject) == ("ann@example.com", "Potwierdź adres e-mail")
    assert "/confirm-email?token=" in letter.body

    confirmed = await _call(
        db_session, "POST", "/auth/confirm-email", json={"token": _token_in(letter)}
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["email_confirmed"] is True


@pytest.mark.asyncio
async def test_until_confirmed_uploads_and_household_invites_are_refused(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email_confirmed_at=None)

    upload = await _call(db_session, "POST", "/receipts/upload", user=user)
    household = await _call(
        db_session, "POST", "/api/v1/household", json={"name": "Home"}, user=user
    )
    profile = await _call(db_session, "GET", "/users/me", user=user)

    assert upload.status_code == household.status_code == 403
    assert upload.json()["code"] == household.json()["code"] == "email_not_confirmed"
    assert profile.status_code == 200


@pytest.mark.asyncio
async def test_an_expired_or_foreign_confirmation_link_is_refused(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email_confirmed_at=None)
    expired = create_link_token(
        "confirm_email", str(user.id), timedelta(seconds=-1), email=user.email
    )
    other_address = create_link_token(
        "confirm_email", str(user.id), timedelta(hours=1), email="old@example.com"
    )

    for token in (expired, other_address, "not-a-token"):
        response = await _call(db_session, "POST", "/auth/confirm-email", json={"token": token})
        assert response.status_code == 400
        assert response.json()["code"] == "link_invalid"
    assert user.email_confirmed_at is None


@pytest.mark.asyncio
async def test_a_link_from_a_letter_is_never_a_session(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    link = create_link_token("confirm_email", str(user.id), timedelta(hours=1), email=user.email)

    response = await _call(db_session, "GET", "/users/me", token=link)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_the_link_is_sent_again_only_while_the_address_is_unconfirmed(
    db_session: AsyncSession,
) -> None:
    waiting = await UserFactory.create_async(email_confirmed_at=None)
    confirmed = await UserFactory.create_async()
    mailer = RecordingMailer()

    for user in (waiting, confirmed):
        response = await _call(
            db_session, "POST", "/users/me/confirmation/resend", user=user, mailer=mailer
        )
        assert response.status_code == 202

    assert [letter.to for letter in mailer.letters] == [waiting.email]


@pytest.mark.asyncio
async def test_throwaway_and_undeliverable_addresses_cannot_sign_up(
    db_session: AsyncSession,
) -> None:
    throwaway = await _sign_up(db_session, "x@mailinator.com", RecordingMailer())
    misspelt = await _call(
        db_session,
        "POST",
        "/auth/register",
        json={"email": "x@gmial.con", "password": PASSWORD, "first_name": "A", "last_name": "B"},
        dns=NoMailDomains(),
    )

    assert throwaway.json()["code"] == "disposable_email"
    assert misspelt.json()["code"] == "email_domain_unreachable"
    assert misspelt.json()["params"] == {"domain": "gmial.con"}
    users = await db_session.scalars(select(User).where(User.email.in_(["x@mailinator.com"])))
    assert users.all() == []


@pytest.mark.asyncio
async def test_forgot_password_answers_alike_whether_the_address_has_an_account(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async(email="known@example.com")
    mailer = RecordingMailer()

    known = await _call(
        db_session,
        "POST",
        "/auth/password/forgot",
        json={"email": user.email, "language": "en"},
        mailer=mailer,
    )
    unknown = await _call(
        db_session,
        "POST",
        "/auth/password/forgot",
        json={"email": "nobody@example.com"},
        mailer=mailer,
    )

    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())
    assert [letter.to for letter in mailer.letters] == ["known@example.com"]


@pytest.mark.asyncio
async def test_a_reset_link_sets_a_new_password_once_and_ends_every_session(
    db_session: AsyncSession,
) -> None:
    mailer = RecordingMailer()
    await _sign_up(db_session, "reset@example.com", mailer)
    await _call(
        db_session,
        "POST",
        "/auth/password/forgot",
        json={"email": "reset@example.com"},
        mailer=mailer,
    )
    token = _token_in(mailer.letters[-1])
    new = {"token": token, "password": "Brand-New-Secret-7"}

    first = await _call(db_session, "POST", "/auth/password/reset", json=new)
    again = await _call(db_session, "POST", "/auth/password/reset", json=new)
    signed_in = await _call(
        db_session,
        "POST",
        "/auth/login",
        json={"email": "reset@example.com", "password": "Brand-New-Secret-7"},
    )

    assert first.status_code == 200
    assert (again.status_code, again.json()["code"]) == (400, "link_invalid")
    assert signed_in.status_code == 200
    user = await db_session.scalar(select(User).where(User.email == "reset@example.com"))
    assert user is not None and user.email_confirmed
    sessions = await db_session.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id))
    live = [s for s in sessions if s.revoked_at is None]
    assert len(live) == 1  # only the sign-in after the reset


@pytest.mark.asyncio
async def test_the_address_changes_only_once_the_link_sent_to_it_is_followed(
    db_session: AsyncSession,
) -> None:
    mailer = RecordingMailer()
    await _sign_up(db_session, "before@example.com", mailer)
    user = await db_session.scalar(select(User).where(User.email == "before@example.com"))
    assert user is not None

    asked = await _call(
        db_session,
        "POST",
        "/users/me/email",
        json={"email": "after@example.com", "password": PASSWORD},
        user=user,
        mailer=mailer,
    )

    assert asked.status_code == 202
    assert user.email == "before@example.com"
    change = mailer.letters[-1]
    assert change.to == "after@example.com"

    switched = await _call(
        db_session,
        "POST",
        "/auth/email/confirm-change",
        json={"token": _token_in(change)},
        mailer=mailer,
    )

    assert switched.json()["email"] == "after@example.com"
    assert switched.json()["email_confirmed"] is True
    assert mailer.letters[-1].to == "before@example.com"
    assert "after@example.com" in mailer.letters[-1].body
    reused = await _call(
        db_session, "POST", "/auth/email/confirm-change", json={"token": _token_in(change)}
    )
    assert reused.json()["code"] == "link_invalid"


@pytest.mark.asyncio
async def test_changing_the_address_needs_the_password_and_a_free_address(
    db_session: AsyncSession,
) -> None:
    mailer = RecordingMailer()
    await _sign_up(db_session, "owner@example.com", mailer)
    user = await db_session.scalar(select(User).where(User.email == "owner@example.com"))
    other = await UserFactory.create_async(email="taken@example.com")

    wrong = await _call(
        db_session,
        "POST",
        "/users/me/email",
        json={"email": "new@example.com", "password": "not-it"},
        user=user,
    )
    taken = await _call(
        db_session,
        "POST",
        "/users/me/email",
        json={"email": other.email, "password": PASSWORD},
        user=user,
    )
    throwaway = await _call(
        db_session,
        "POST",
        "/users/me/email",
        json={"email": "me@mailinator.com", "password": PASSWORD},
        user=user,
    )

    assert (wrong.status_code, wrong.json()["code"]) == (403, "invalid_credentials")
    assert taken.json()["code"] == "email_taken"
    assert throwaway.json()["code"] == "disposable_email"
