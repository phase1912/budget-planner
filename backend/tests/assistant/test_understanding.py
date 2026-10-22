"""An assistant that finds what the user means (F21.13), hears them (F21.2.2) and takes the
files they attach (F21.8.2): it is told what the user has — never anyone else's (N2) — asks
with options to tap, finds products and the family's spending, and starts nothing it should
not."""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.assistant.api import get_speech
from app.assistant.core.ports import ToolCall
from app.assistant.tools.accounts import find_account
from app.assistant.tools.base import ToolContext
from app.assistant.tools.overview import known
from app.core.config import get_settings
from app.core.context import current_user_id
from app.db.session import get_db_session
from app.main import create_app
from app.models.user import User
from app.ports.speech import SpeechUnavailable
from app.repository.category import CategoryRepository
from app.repository.household import HouseholdRepository
from app.services.household import HouseholdService
from app.services.manual_expense import ManualExpense, record_expense
from tests.assistant.test_api import URL, ScriptedAssistant, _call, _say
from tests.assistant.test_tools import _approve, _propose
from tests.factories.upload_job import UploadJobFactory
from tests.factories.user import UserFactory

TODAY = datetime(2026, 10, 20, tzinfo=UTC).date()


async def _cards(session: AsyncSession, user: User, *names: str) -> None:
    for name in names:
        [card] = await _propose(
            session, user, ToolCall("add_account", {"name": name, "balance": "100"})
        )
        await _approve(session, user, card)


async def _bought(session: AsyncSession, user: User, *names: str) -> None:
    current_user_id.set(user.id)
    groceries = next(
        c
        for c in await CategoryRepository(session).list_available(user.id)
        if c.name == "Groceries"
    )
    for name in names:
        await record_expense(
            session, user, ManualExpense(name, TODAY, Decimal("5.00"), None, groceries.id), None
        )


@pytest.mark.asyncio
async def test_the_model_is_told_the_users_cards_by_number_and_role_and_nothing_of_others(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    other = await UserFactory.create_async(currency="PLN")
    await _cards(db_session, other, "Theirs")
    await _cards(db_session, me, "Main", "Revolut")
    [bill] = await _propose(db_session, me, ToolCall("add_bill", {"name": "Rent", "amount": "9"}))
    await _approve(db_session, me, bill)
    current_user_id.set(me.id)

    summary = await known(ToolContext(db_session, me, TODAY))

    assert "1. Main — card, pays for purchases" in summary
    assert "2. Revolut — card," in summary
    assert "Rent 9.00" in summary
    assert "Theirs" not in summary


@pytest.mark.asyncio
async def test_a_card_is_found_by_its_number_or_as_the_one_paying_for_purchases(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    await _cards(db_session, me, "Main", "Revolut")
    current_user_id.set(me.id)
    ctx = ToolContext(db_session, me, TODAY)

    second, _ = await find_account(ctx, "2")
    paying, _ = await find_account(ctx, "purchase card")
    missing, error = await find_account(ctx, "9")

    assert (second and second.name, paying and paying.name) == ("Revolut", "Main")
    assert missing is None and "Main, Revolut" in (error or "")


@pytest.mark.asyncio
async def test_a_question_with_options_is_kept_and_read_back_with_them(
    db_session: AsyncSession,
) -> None:
    class Asking(ScriptedAssistant):
        async def reply(self, history: Any, *args: Any, **kwargs: Any) -> Any:
            from app.assistant.core.ports import AssistantReply

            self.seen = list(history)
            return AssistantReply("Which card?", [], ["Main", "Revolut"])

    me = await UserFactory.create_async(currency="PLN")
    asked = await _say(db_session, me, "update the balance", Asking())
    again = Asking()
    await _say(db_session, me, "Revolut", again, conversation=asked["id"])

    choice = asked["messages"][-1]
    assert (choice["card"]["kind"], choice["card_state"]) == ("choice", "shown")
    assert choice["card"]["fields"]["options"] == ["Main", "Revolut"]
    assert "(Options offered: Main, Revolut)" in again.seen[-2].text


@pytest.mark.asyncio
async def test_products_are_found_by_any_spelling_and_grouped_on_a_card(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    other = await UserFactory.create_async(currency="PLN")
    await _bought(db_session, me, "Chipsy Lay's", "Coca-Cola 1l", "Mleko 2%")
    await _bought(db_session, other, "Chipsy Crunchips")
    finding = ScriptedAssistant(reads=[ToolCall("find_products", {"words": ["chips", "chipsy"]})])
    await _say(db_session, me, "what chips did I buy?", finding)

    [group] = await _propose(
        db_session,
        me,
        ToolCall(
            "save_product_group", {"name": "Snacks", "products": ["Chipsy Lay's", "Coca-Cola 1l"]}
        ),
    )
    saved = await _approve(db_session, me, group)
    refused = await _propose(
        db_session,
        me,
        ToolCall("save_product_group", {"name": "X", "products": ["Chipsy Crunchips"]}),
    )

    found = json.loads(finding.read_results[0])
    assert [p["name"] for p in found["products"]] == ["Chipsy Lay's"]
    assert group["card"]["fields"]["products"] == ["Chipsy Lay's", "Coca-Cola 1l"]
    assert [f["kind"] for f in group["card"]["form"]] == ["text", "items"]
    assert saved["saved_ref"].startswith("product_group:")
    assert refused == []


@pytest.mark.asyncio
async def test_the_familys_spending_names_who_spent_and_says_when_there_is_no_family(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN", first_name="Bohdan")
    wife = await UserFactory.create_async(currency="PLN", first_name="Olena")
    alone = await UserFactory.create_async(currency="PLN")
    households = HouseholdService(HouseholdRepository(db_session))
    family = await households.create(me, "Home")
    await households.join(wife, family.invite_code)
    await _bought(db_session, wife, "Sushi")
    asking = ScriptedAssistant(reads=[ToolCall("family_spending", {"member": "olena"})])
    lonely = ScriptedAssistant(reads=[ToolCall("family_spending", {})])

    await _say(db_session, me, "how does my wife spend?", asking)
    await _say(db_session, alone, "and my family?", lonely)

    figures = json.loads(asking.read_results[0])
    assert [(m["name"], m["total"]) for m in figures["members"]] == [("Olena", "5.00")]
    assert json.loads(lonely.read_results[0]) == {"error": "the user is in no family"}


class Hearing:
    """A recogniser at the port: hears the same words, or fails."""

    def __init__(self, said: str = "taxi 45", fails: bool = False) -> None:
        self.said, self.fails = said, fails
        self.heard: list[tuple[bytes, str, str]] = []

    async def recognise(self, audio: bytes, mime_type: str, language: str) -> str:
        if self.fails:
            raise SpeechUnavailable("down")
        self.heard.append((audio, mime_type, language))
        return self.said


async def _speak(session: AsyncSession, user: User, audio: bytes, speech: Hearing) -> Any:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield session

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_speech] = lambda: speech
    token = jwt.encode(
        {"sub": str(user.id)}, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS256"
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        return await client.post(
            f"{URL}/speech", files={"audio": ("speech.wav", audio, "audio/wav")}
        )


@pytest.mark.asyncio
async def test_a_recording_comes_back_as_words_in_the_users_language_and_nothing_is_kept(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(language="uk")
    hearing = Hearing("таксі 45")

    answered = await _speak(db_session, me, b"RIFF....WAVE", hearing)
    too_long = await _speak(db_session, me, b"0" * 2_000_001, Hearing())
    failed = await _speak(db_session, me, b"RIFF", Hearing(fails=True))

    assert (answered.status_code, answered.json()) == (200, {"text": "таксі 45"})
    assert hearing.heard == [(b"RIFF....WAVE", "audio/wav", "uk")]
    assert (too_long.status_code, too_long.json()["code"]) == (413, "speech_too_long")
    assert (failed.status_code, failed.json()["code"]) == (503, "speech_unavailable")


@pytest.mark.asyncio
async def test_attached_receipts_follow_their_reading_and_another_users_reading_is_not_found(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async()
    other = await UserFactory.create_async()
    mine = await UploadJobFactory.create_async(user_id=me.id, total_items=2)
    theirs = await UploadJobFactory.create_async(user_id=other.id, total_items=1)
    assistant = ScriptedAssistant()

    sent = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/messages",
        {"text": "add these", "upload_job_id": str(mine.id), "attached": 2, "today": str(TODAY)},
        assistant,
    )
    refused = await _call(
        db_session,
        me,
        "POST",
        f"{URL}/messages",
        {"text": "add these", "upload_job_id": str(theirs.id), "attached": 1},
    )

    attachment = sent.json()["messages"][1]
    assert attachment["card"] == {
        "kind": "attachment",
        "fields": {"job_id": str(mine.id), "count": 2},
        "form": None,
    }
    assert "attached 2 receipt file(s)" in assistant.seen[-1].text
    assert refused.status_code == 404
