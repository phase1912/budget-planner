"""The service's own analytics: who did what, and how often pages are read (F17.3, N2)."""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_mail_domain_resolver, get_mailer
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db_session
from app.domain.activity import ActivityKind
from app.main import create_app
from app.models.activity import ActivityEvent, PageViewCount
from app.models.user import User
from app.services.activity import ActivityService
from tests.factories.category import CategoryFactory
from tests.factories.user import UserFactory

PASSWORD = "Correct-Horse-42"
BROWSER = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) Safari/604.1"


class NoMail:
    async def deliver(self, letter: Any) -> bool:
        return True


async def _call(
    session: AsyncSession,
    method: str,
    url: str,
    *,
    json: Any = None,
    user: User | None = None,
    agent: str = BROWSER,
) -> Response:
    async def same_session() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = same_session
    app.dependency_overrides[get_mailer] = lambda: NoMail()
    app.dependency_overrides[get_mail_domain_resolver] = lambda: None
    headers = {"User-Agent": agent}
    if user is not None:
        headers["Authorization"] = f"Bearer {create_access_token(user.id)}"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as client:
        return await client.request(method, url, json=json)


async def _events(session: AsyncSession, user_id: Any) -> list[str]:
    rows = await session.scalars(
        select(ActivityEvent.event)
        .where(ActivityEvent.user_id == user_id)
        .order_by(ActivityEvent.created_at)
    )
    return list(rows)


@pytest.fixture(autouse=True)
def forget_who_was_seen() -> None:
    ActivityService._seen_today.clear()


@pytest.mark.asyncio
async def test_signing_up_signing_in_and_using_the_app_are_recorded_once_a_day(
    db_session: AsyncSession,
) -> None:
    body = {
        "email": "ann@example.com",
        "password": PASSWORD,
        "first_name": "Ann",
        "last_name": "Lee",
        "accept_terms": True,
    }
    await _call(db_session, "POST", "/auth/register", json=body)
    await _call(
        db_session, "POST", "/auth/login", json={"email": body["email"], "password": PASSWORD}
    )
    user = await db_session.scalar(select(User).where(User.email == "ann@example.com"))
    assert user is not None
    for _ in range(3):
        await _call(db_session, "GET", "/users/me", user=user)

    assert await _events(db_session, user.id) == [
        ActivityKind.SIGNED_UP,
        ActivityKind.SIGNED_IN,
        ActivityKind.ACTIVE,
    ]


@pytest.mark.asyncio
async def test_a_view_of_a_public_page_is_counted_by_page_and_source_only(
    db_session: AsyncSession,
) -> None:
    view = {"page": "/help", "referrer": "https://www.google.com/search?q=receipts", "entry": True}

    for _ in range(2):
        response = await _call(db_session, "POST", "/api/v1/analytics/views", json=view)
        assert response.status_code == 204
    await _call(db_session, "POST", "/api/v1/analytics/views", json={"page": "/receipts"})
    await _call(db_session, "POST", "/api/v1/analytics/views", json=view, agent="Googlebot/2.1")

    rows = (await db_session.execute(select(PageViewCount))).scalars().all()
    assert [(r.page, r.source, r.views, r.entries) for r in rows] == [("/help", "google", 2, 2)]
    # Nothing about the visitor: the table has no column that could hold it.
    assert set(PageViewCount.__table__.c.keys()) == {
        "id",
        "created_at",
        "updated_at",
        "day",
        "page",
        "source",
        "views",
        "entries",
    }


@pytest.mark.asyncio
async def test_the_report_is_for_admins_only_and_counts_without_naming_anyone(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)
    admin = await UserFactory.create_async(email="boss@example.com", created_at=now)
    user = await UserFactory.create_async(email_confirmed_at=None, created_at=now)
    monkeypatch.setattr(get_settings(), "admin_emails", ["boss@example.com"])
    await _call(db_session, "POST", "/api/v1/analytics/views", json={"page": "/", "entry": True})
    await _call(db_session, "GET", "/users/me", user=user)
    today = date.today().isoformat()
    url = f"/api/v1/analytics/report?start={today}&end={today}"

    refused = await _call(db_session, "GET", url, user=user)
    report = await _call(db_session, "GET", url, user=admin)

    assert (refused.status_code, refused.json()["code"]) == (403, "permission_denied")
    figures = report.json()
    assert figures["visits"] == 1
    assert figures["visits_by_source"] == [{"name": "direct", "count": 1}]
    # The admin, who reads the report and so is active too, is in no user figure.
    assert (figures["sign_ups"], figures["confirmed"], figures["active_week"]) == (1, 0, 1)
    assert "ann@example.com" not in report.text and user.email not in report.text


@pytest.mark.asyncio
async def test_activity_older_than_a_year_is_pruned(db_session: AsyncSession) -> None:
    user = await UserFactory.create_async()
    now = datetime.now(UTC)
    db_session.add_all(
        [
            ActivityEvent(user_id=user.id, event="active", created_at=now - timedelta(days=400)),
            ActivityEvent(user_id=user.id, event="active", created_at=now - timedelta(days=10)),
        ]
    )
    await db_session.flush()

    removed = await ActivityService(db_session).prune(now)

    count = await db_session.scalar(
        select(func.count()).select_from(ActivityEvent).where(ActivityEvent.user_id == user.id)
    )
    assert (removed, count) == (1, 1)


@pytest.mark.asyncio
async def test_pruning_that_fails_never_stops_the_service_starting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Housekeeping only: a start before the migration ran must still serve (ADR-0014)."""
    from app import main

    async def broken(self: ActivityService, now: datetime) -> int:
        raise RuntimeError("relation activity_events does not exist")

    monkeypatch.setattr(ActivityService, "prune", broken)

    await main._prune_activity()


@pytest.mark.asyncio
async def test_a_visitor_from_instagram_who_signs_up_adds_up_exactly_once_on_the_dashboard(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole path, as the dashboard must count it: one visit, two page views, one
    sign-up who confirmed and added an expense — and the admin testing alongside, nowhere.
    """
    now = datetime.now(UTC)
    admin = await UserFactory.create_async(email="boss@example.com", created_at=now)
    monkeypatch.setattr(get_settings(), "admin_emails", ["boss@example.com"])
    instagram = "https://l.instagram.com/?u=https%3A%2F%2Fbudget-agent.web.app%2F"
    # Lands from Instagram, then moves on to sign up: the second page is the same visit.
    await _call(
        db_session,
        "POST",
        "/api/v1/analytics/views",
        json={"page": "/", "referrer": instagram, "entry": True},
    )
    await _call(
        db_session,
        "POST",
        "/api/v1/analytics/views",
        json={"page": "/register", "referrer": instagram, "entry": False},
    )
    await _call(
        db_session,
        "POST",
        "/auth/register",
        json={
            "email": "kent@example.com",
            "password": PASSWORD,
            "first_name": "Kent",
            "last_name": "B",
            "accept_terms": True,
        },
    )
    kent = await db_session.scalar(select(User).where(User.email == "kent@example.com"))
    assert kent is not None
    kent.email_confirmed_at = now
    await db_session.flush()
    expense = {"description": "Coffee", "amount": "12.00", "spent_on": now.date().isoformat()}
    for spender in (kent, admin):  # the admin uses the app the same day; none of it may show
        category = await CategoryFactory.create_async(user_id=spender.id)
        added = await _call(
            db_session,
            "POST",
            "/receipts/manual",
            json={**expense, "category_id": str(category.id)},
            user=spender,
        )
        assert added.status_code == 201, added.text
    today = now.date().isoformat()

    figures = (
        await _call(
            db_session, "GET", f"/api/v1/analytics/report?start={today}&end={today}", user=admin
        )
    ).json()

    assert (figures["visits"], figures["page_views"]) == (1, 2)
    assert figures["visits_by_source"] == [{"name": "instagram", "count": 1}]
    assert figures["views_by_page"] == [
        {"name": "/", "count": 1},
        {"name": "/register", "count": 1},
    ]
    assert (figures["sign_ups"], figures["confirmed"], figures["with_a_receipt"]) == (1, 1, 1)
    assert (figures["active_week"], figures["active_month"], figures["returning"]) == (1, 1, 0)
    [day] = figures["days"]
    assert (day["visits"], day["page_views"], day["sign_ups"], day["confirmations"]) == (
        1,
        2,
        1,
        1,
    )
    assert await _events(db_session, kent.id) == [
        ActivityKind.SIGNED_UP,
        ActivityKind.ACTIVE,
        ActivityKind.RECEIPT_STORED,
    ]
