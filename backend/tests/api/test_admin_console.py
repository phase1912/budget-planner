"""The admin console: finding and supporting accounts, plans and the log (F18.6, F18.4, N2)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_mailer
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.main import create_app
from app.models.user import User
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

BOSS = "boss@example.com"


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
    user: User,
    json: Any = None,
    outbox: Outbox | None = None,
) -> Response:
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    app.dependency_overrides[get_mailer] = lambda: outbox or Outbox()
    token = create_access_token(user.id, second_factor=True)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.request(method, url, json=json)


@pytest.fixture
def super_admins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "admin_emails", [BOSS])


@pytest.mark.asyncio
async def test_the_console_does_not_exist_for_an_ordinary_account(
    db_session: AsyncSession,
) -> None:
    user = await UserFactory.create_async()
    other = await UserFactory.create_async()

    for method, url in [
        ("GET", "/api/v1/admin/users"),
        ("GET", f"/api/v1/admin/users/{other.id}"),
        ("POST", f"/api/v1/admin/users/{other.id}/confirm-email"),
        ("GET", "/api/v1/admin/log"),
    ]:
        assert (await _call(db_session, method, url, user=user)).status_code == 403


@pytest.mark.asyncio
async def test_an_admin_finds_accounts_by_address_and_filters(
    db_session: AsyncSession,
) -> None:
    admin = await UserFactory.create_async(role="admin")
    ann = await UserFactory.create_async(email="ann_smith@example.com")
    await UserFactory.create_async(email="annex@example.com", email_confirmed_at=None)
    await UserFactory.create_async(email="bob@example.com")

    found = await _call(db_session, "GET", "/api/v1/admin/users?q=ann", user=admin)
    assert found.status_code == 200
    assert found.json()["total"] == 2
    # "_" is a literal underscore in the search, not a wildcard.
    exact = await _call(db_session, "GET", "/api/v1/admin/users?q=ann_", user=admin)
    assert [row["email"] for row in exact.json()["items"]] == [ann.email]
    unconfirmed = await _call(
        db_session, "GET", "/api/v1/admin/users?q=ann&confirmed=false", user=admin
    )
    assert [row["email"] for row in unconfirmed.json()["items"]] == ["annex@example.com"]


@pytest.mark.asyncio
async def test_the_user_card_shows_facts_and_activity_never_receipts(
    db_session: AsyncSession,
) -> None:
    admin = await UserFactory.create_async(role="admin")
    user = await UserFactory.create_async()
    await ReceiptFactory.create_async(user_id=user.id, merchant_name="Secret shop")

    card = await _call(db_session, "GET", f"/api/v1/admin/users/{user.id}", user=admin)
    assert card.status_code == 200
    body = card.json()
    assert body["email"] == user.email
    assert body["plan"] == "free"
    assert "Secret shop" not in card.text
    assert not {"receipts", "line_items", "password_hash", "two_factor_secret"} & body.keys()

    missing = await _call(
        db_session, "GET", "/api/v1/admin/users/00000000-0000-0000-0000-000000000000", user=admin
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_a_granted_plan_raises_the_limit_extends_and_can_be_taken_back(
    db_session: AsyncSession,
) -> None:
    admin = await UserFactory.create_async(role="admin")
    user = await UserFactory.create_async()
    url = f"/api/v1/admin/users/{user.id}"

    first = await _call(
        db_session, "POST", f"{url}/grants", user=admin, json={"days": 30, "reason": "Beta tester"}
    )
    assert first.status_code == 201
    quota = (await _call(db_session, "GET", "/users/me/quota", user=user)).json()
    assert quota["plan"] == "paid"
    assert quota["limit"] == get_settings().paid_monthly_credits
    assert quota["ad_free"] is True

    second = await _call(
        db_session, "POST", f"{url}/grants", user=admin, json={"days": 10, "reason": "Extension"}
    )
    # Granting again while a plan runs adds days after it.
    assert second.json()["starts_at"] == first.json()["ends_at"]
    expected_end = datetime.now(UTC) + timedelta(days=40)
    card = (await _call(db_session, "GET", url, user=admin)).json()
    assert card["plan_ends_on"] in {
        (expected_end - timedelta(days=d)).date().isoformat() for d in (0, 1)
    }

    for grant in (first.json(), second.json()):
        revoked = await _call(db_session, "POST", f"{url}/grants/{grant['id']}/revoke", user=admin)
        assert revoked.status_code == 204
    quota = (await _call(db_session, "GET", "/users/me/quota", user=user)).json()
    assert quota["plan"] == "free"
    assert quota["limit"] == get_settings().free_monthly_credits


@pytest.mark.asyncio
async def test_a_grant_of_another_account_cannot_be_revoked_through_this_one(
    db_session: AsyncSession,
) -> None:
    admin = await UserFactory.create_async(role="admin")
    ann = await UserFactory.create_async()
    bob = await UserFactory.create_async()
    grant = await _call(
        db_session,
        "POST",
        f"/api/v1/admin/users/{ann.id}/grants",
        user=admin,
        json={"days": 30, "reason": "Support"},
    )
    wrong = await _call(
        db_session,
        "POST",
        f"/api/v1/admin/users/{bob.id}/grants/{grant.json()['id']}/revoke",
        user=admin,
    )
    assert wrong.status_code == 404


@pytest.mark.asyncio
async def test_support_actions_confirm_and_send_links_but_never_set_a_password(
    db_session: AsyncSession,
) -> None:
    admin = await UserFactory.create_async(role="admin")
    user = await UserFactory.create_async(email_confirmed_at=None)
    url = f"/api/v1/admin/users/{user.id}"
    outbox = Outbox()

    sent = await _call(db_session, "POST", f"{url}/send-confirmation", user=admin, outbox=outbox)
    assert sent.status_code == 204
    assert (await _call(db_session, "POST", f"{url}/confirm-email", user=admin)).status_code == 204
    assert (await _call(db_session, "GET", url, user=admin)).json()["email_confirmed_at"]
    again = await _call(db_session, "POST", f"{url}/send-confirmation", user=admin)
    assert again.status_code == 409
    assert again.json()["code"] == "already_confirmed"

    reset = await _call(db_session, "POST", f"{url}/send-password-reset", user=admin, outbox=outbox)
    assert reset.status_code == 204
    assert [letter.to for letter in outbox.letters] == [user.email, user.email]
    assert "reset-password" in outbox.letters[1].body


@pytest.mark.asyncio
async def test_only_a_super_admin_appoints_admins_and_no_one_changes_a_super_admin(
    db_session: AsyncSession, super_admins: None
) -> None:
    boss = await UserFactory.create_async(email=BOSS)
    admin = await UserFactory.create_async(role="admin")
    user = await UserFactory.create_async()
    role = f"/api/v1/admin/users/{user.id}/role"

    by_admin = await _call(db_session, "PUT", role, user=admin, json={"admin": True})
    assert by_admin.status_code == 403
    assert by_admin.json()["code"] == "super_admin_only"

    assert (
        await _call(db_session, "PUT", role, user=boss, json={"admin": True})
    ).status_code == 204
    me = (await _call(db_session, "GET", "/users/me", user=user)).json()
    assert me["is_admin"] is True and me["is_super_admin"] is False

    fixed = await _call(
        db_session, "PUT", f"/api/v1/admin/users/{boss.id}/role", user=boss, json={"admin": False}
    )
    assert fixed.status_code == 409
    assert fixed.json()["code"] == "admin_role_fixed"


@pytest.mark.asyncio
async def test_every_action_is_logged_and_only_super_admins_read_the_log(
    db_session: AsyncSession, super_admins: None
) -> None:
    boss = await UserFactory.create_async(email=BOSS)
    admin = await UserFactory.create_async(role="admin")
    user = await UserFactory.create_async(email="client@example.com")
    url = f"/api/v1/admin/users/{user.id}"

    await _call(db_session, "POST", f"{url}/confirm-email", user=admin)
    await _call(
        db_session, "POST", f"{url}/grants", user=admin, json={"days": 7, "reason": "Trial"}
    )
    await _call(db_session, "PUT", f"{url}/role", user=boss, json={"admin": True})

    assert (await _call(db_session, "GET", "/api/v1/admin/log", user=admin)).status_code == 403
    log = (await _call(db_session, "GET", "/api/v1/admin/log", user=boss)).json()["items"]
    assert [(e["action"], e["admin"], e["target"]) for e in log] == [
        ("admin_appointed", BOSS, "client@example.com"),
        ("plan_granted", admin.email, "client@example.com"),
        ("email_confirmed", admin.email, "client@example.com"),
    ]
    assert log[1]["details"]["reason"] == "Trial"


@pytest.mark.asyncio
async def test_an_admin_shows_the_first_sign_in_setup_again_even_to_themselves(
    db_session: AsyncSession, super_admins: None
) -> None:
    boss = await UserFactory.create_async(email=BOSS, onboarded_at=datetime.now(UTC))
    admin = await UserFactory.create_async(role="admin", onboarded_at=datetime.now(UTC))
    user = await UserFactory.create_async(onboarded_at=datetime.now(UTC), currency="PLN")

    for target in (user, admin):
        url = f"/api/v1/admin/users/{target.id}"
        restarted = await _call(db_session, "POST", f"{url}/restart-onboarding", user=admin)
        assert restarted.status_code == 204
        assert (await _call(db_session, "GET", url, user=admin)).json()["onboarded_at"] is None
    # Only the "done" mark goes: what the setup chose before stays.
    assert user.currency == "PLN"

    plain = await UserFactory.create_async()
    refused = await _call(
        db_session, "POST", f"/api/v1/admin/users/{user.id}/restart-onboarding", user=plain
    )
    assert refused.status_code == 403
    log = (await _call(db_session, "GET", "/api/v1/admin/log", user=boss)).json()["items"]
    assert [e["action"] for e in log] == ["onboarding_restarted", "onboarding_restarted"]
