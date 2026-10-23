"""Reporting an assistant reply (F22.4.2): its words and the reason kept for the admins,
never the conversation around it — and only the user's own replies (N2)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.conversation import ReplyReport
from app.services.admin import AdminService
from tests.assistant.test_api import URL, _call, _say
from tests.factories.user import UserFactory


def _reply(conversation: dict[str, object]) -> str:
    messages = conversation["messages"]
    assert isinstance(messages, list)
    return next(str(m["id"]) for m in messages if m["role"] == "assistant" and m["text"])


@pytest.mark.asyncio
async def test_a_reported_reply_is_kept_with_its_reason_for_the_admins(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(email="ann@example.com")
    reply = _reply(await _say(db_session, me, "how is my month?"))

    reported = await _call(
        db_session, me, "POST", f"{URL}/messages/{reply}/report", {"reason": "wrong"}
    )
    listed = await AdminService(db_session, get_settings()).reply_reports(10)

    report = (await db_session.execute(select(ReplyReport))).scalar_one()
    assert reported.status_code == 204
    assert (report.reason, report.reply_text) == ("wrong", "answer in en")
    assert [(r.reason, email) for r, email in listed] == [("wrong", "ann@example.com")]


@pytest.mark.asyncio
async def test_another_users_reply_cannot_be_reported(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    theirs = _reply(await _say(db_session, stranger, "how is my month?"))

    response = await _call(
        db_session, me, "POST", f"{URL}/messages/{theirs}/report", {"reason": "offensive"}
    )

    assert response.status_code == 404
    assert (await db_session.execute(select(ReplyReport))).first() is None


@pytest.mark.asyncio
async def test_a_user_cannot_read_the_reports(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()

    response = await _call(db_session, me, "GET", "/api/v1/admin/reports")

    assert response.status_code == 403
