"""Writing to the people running the service (F17.10.2)."""

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app.api.dependencies import get_mailer
from app.core.config import get_settings
from app.main import create_app
from app.ports.email import Letter
from app.services import contact as contact_module
from app.services.contact import AddressThrottle

MESSAGE = {
    "email": "ann@example.com",
    "topic": "question",
    "message": "How is the per diem counted on a business trip?",
    "language": "pl",
}


class RecordingMailer:
    def __init__(self) -> None:
        self.letters: list[Letter] = []

    async def deliver(self, letter: Letter) -> bool:
        self.letters.append(letter)
        return True


async def _send(body: dict[str, Any], mailer: RecordingMailer) -> Response:
    app = create_app()
    app.dependency_overrides[get_mailer] = lambda: mailer
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/api/v1/contact", json=body)


@pytest.fixture(autouse=True)
def fresh_throttle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(contact_module, "THROTTLE", AddressThrottle())
    monkeypatch.setattr("app.api.routers.contact.THROTTLE", contact_module.THROTTLE)
    monkeypatch.setattr(get_settings(), "admin_emails", ["admin@example.com"])
    monkeypatch.setattr(get_settings(), "support_email", None)


@pytest.mark.asyncio
async def test_a_message_reaches_the_administrators_answerable_by_reply_with_a_copy_back() -> None:
    mailer = RecordingMailer()

    response = await _send(MESSAGE, mailer)

    assert response.status_code == 202
    to_admin, copy = mailer.letters
    assert (to_admin.to, to_admin.reply_to) == ("admin@example.com", "ann@example.com")
    assert "per diem" in to_admin.body and "question" in to_admin.subject
    assert (copy.to, copy.subject) == ("ann@example.com", "Otrzymaliśmy Twoją wiadomość")
    assert "per diem" in copy.body


@pytest.mark.asyncio
async def test_a_bot_filling_the_trap_field_is_told_it_worked_and_nothing_is_sent() -> None:
    mailer = RecordingMailer()

    response = await _send({**MESSAGE, "website": "http://spam.example"}, mailer)

    assert response.status_code == 202
    assert mailer.letters == []


@pytest.mark.asyncio
async def test_one_address_writing_too_often_is_refused() -> None:
    mailer = RecordingMailer()

    answers = [(await _send(MESSAGE, mailer)).status_code for _ in range(4)]

    assert answers == [202, 202, 202, 429]
    assert len(mailer.letters) == 6


@pytest.mark.parametrize("message", ["too short", "x" * 4001])
@pytest.mark.asyncio
async def test_a_message_too_short_or_too_long_is_refused(message: str) -> None:
    response = await _send({**MESSAGE, "message": message}, RecordingMailer())

    assert response.status_code == 422


def test_the_window_frees_up_once_it_has_passed() -> None:
    throttle = AddressThrottle(limit=1, window=60)
    throttle.admit("A@example.com", now=0)
    with pytest.raises(contact_module.TooManyMessagesError):
        throttle.admit("a@example.com", now=30)
    throttle.admit("a@example.com", now=61)


@pytest.mark.asyncio
async def test_with_a_support_mailbox_messages_go_there_not_to_the_administrators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F22.1.2: the store listing's public contact answers the contact form too."""
    monkeypatch.setattr(get_settings(), "support_email", "support@example.com")
    mailer = RecordingMailer()

    await _send(MESSAGE, mailer)

    assert [letter.to for letter in mailer.letters] == ["support@example.com", "ann@example.com"]
