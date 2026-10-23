"""Receipts and categories talked about in the chat (F21.15): the latest receipt by id, its
lines with their categories, a new category and a move into it on cards — only ever the
caller's own (N2)."""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.core.ports import ToolCall
from app.assistant.service import CardState, _history
from app.assistant.tools.toolbox import Toolbox
from app.core.context import current_user_id
from app.models.category import Category
from app.models.conversation import ConversationMessage
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.user import User
from tests.assistant.test_tools import _approve, _propose
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

TODAY = datetime.now(UTC).date()


def _toolbox(session: AsyncSession, user: User) -> Toolbox:
    current_user_id.set(user.id)
    return Toolbox(session, user, TODAY)


async def _youtube(owner: User) -> Receipt:
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id,
        merchant_name="YouTube",
        transaction_date=datetime.now(UTC),
        total_amount=Decimal("60.00"),
        file_ids=[],
    )
    await LineItemFactory.create_async(
        receipt=receipt,
        name="YouTube Premium",
        quantity=Decimal(1),
        unit_price=Decimal("60.00"),
        total_price=Decimal("60.00"),
        category=None,
        position=0,
    )
    return receipt


@pytest.mark.asyncio
async def test_the_latest_receipt_comes_with_an_id_and_its_lines_with_their_categories(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async(currency="PLN")
    receipt = await _youtube(me)
    toolbox = _toolbox(db_session, me)

    latest = json.loads(await toolbox.read(ToolCall("receipts", {})))
    lines = json.loads(
        await toolbox.read(ToolCall("receipt_lines", {"receipt_id": latest["latest"][0]["id"]}))
    )

    assert latest["latest"][0]["id"] == str(receipt.id)
    assert toolbox.answers["receipts"].fields["refs"][0]["id"] == str(receipt.id)
    assert (lines["shop"], lines["lines"][0]["category"]) == ("YouTube", "Uncategorized")


def test_a_receipt_shown_earlier_keeps_its_id_for_the_next_turn() -> None:
    """The conversation broke at "which category is it?": the id had been dropped."""
    uid = uuid.uuid4()
    shown = ConversationMessage(
        user_id=uid,
        role="assistant",
        text="Your last receipt is YouTube, 60.",
        card={"kind": "answer", "fields": {"screen": "receipts", "refs": [{"id": "r-1"}]}},
        card_state=CardState.SHOWN,
    )

    [turn] = _history([shown])

    assert "r-1" in turn.text


@pytest.mark.asyncio
async def test_create_a_category_and_move_the_receipt_there_is_one_card(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async()
    receipt = await _youtube(me)

    [card] = await _propose(
        db_session,
        me,
        ToolCall("move_to_category", {"receipt_id": str(receipt.id), "category": "Subscriptions"}),
    )
    assert card["card"]["fields"]["category"] == "Subscriptions"
    await _approve(db_session, me, card)

    category = (
        await db_session.execute(
            select(Category).where(Category.user_id == me.id, Category.name == "Subscriptions")
        )
    ).scalar_one()
    line = (
        await db_session.execute(select(LineItem).where(LineItem.receipt_id == receipt.id))
    ).scalar_one()
    assert (line.category_id, line.is_category_manual) == (category.id, True)


@pytest.mark.asyncio
async def test_a_new_category_alone_is_a_card_and_an_existing_name_is_refused(
    db_session: AsyncSession,
) -> None:
    me = await UserFactory.create_async()

    [card] = await _propose(db_session, me, ToolCall("add_category", {"name": "Pets"}))
    await _approve(db_session, me, card)
    refused = await _toolbox(db_session, me).check(ToolCall("add_category", {"name": "pets"}))

    assert refused is not None and "already" in refused


@pytest.mark.asyncio
async def test_another_members_receipt_is_not_refiled_by_chat(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    theirs = await _youtube(stranger)
    toolbox = _toolbox(db_session, me)

    refused = await toolbox.check(
        ToolCall("move_to_category", {"receipt_id": str(theirs.id), "category": "Subscriptions"})
    )
    lines = json.loads(
        await toolbox.read(ToolCall("receipt_lines", {"receipt_id": str(theirs.id)}))
    )

    assert refused is not None and "no receipt of the user's own" in refused
    assert "error" in lines
