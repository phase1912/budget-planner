"""Receipts found, reviewed, corrected and deleted in the chat, and put on trips (F21.6):
each change a card saved through the receipt screen's own services — only ever the caller's
own receipts (N2)."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.assistant.core.ports import ToolCall
from app.assistant.tools.toolbox import Toolbox
from app.core.context import current_user_id
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptChannel, ReceiptStatus
from app.models.trip import Trip
from app.models.user import User
from tests.assistant.test_tools import _approve, _propose
from tests.factories.line_item import LineItemFactory
from tests.factories.receipt import ReceiptFactory
from tests.factories.user import UserFactory

TODAY = datetime.now(UTC).date()


def _toolbox(session: AsyncSession, user: User) -> Toolbox:
    current_user_id.set(user.id)
    return Toolbox(session, user, TODAY)


async def _biedronka(
    owner: User, *, total: str = "10.50", status: ReceiptStatus = ReceiptStatus.PARSED
) -> Receipt:
    receipt = await ReceiptFactory.create_async(
        user_id=owner.id,
        merchant_name="Biedronka",
        transaction_date=datetime(2026, 10, 14, tzinfo=UTC),
        total_amount=Decimal(total),
        status=status,
        file_ids=[],
    )
    for position, (name, price) in enumerate((("Mleko", "4.00"), ("Chleb", "6.50"))):
        await LineItemFactory.create_async(
            receipt=receipt,
            name=name,
            quantity=Decimal(1),
            unit_price=Decimal(price),
            total_price=Decimal(price),
            category=None,
            position=position,
        )
    return receipt


async def _reloaded(session: AsyncSession, receipt: Receipt) -> Receipt:
    receipt_id = receipt.id
    session.expire_all()
    return (await session.execute(select(Receipt).where(Receipt.id == receipt_id))).scalar_one()


@pytest.mark.asyncio
async def test_what_waits_for_review_says_why(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()
    off = await _biedronka(me, total="12.00", status=ReceiptStatus.MANUAL_REVIEW)
    await _biedronka(me)

    figures = json.loads(await _toolbox(db_session, me).read(ToolCall("receipts_to_review", {})))

    [waiting] = figures["receipts"]
    assert waiting["id"] == str(off.id)
    assert "add up to 10.50, not the total 12.00" in waiting["waits_because"][0]


@pytest.mark.asyncio
async def test_a_corrected_price_moves_the_total_with_it(db_session: AsyncSession) -> None:
    """The demo: "on the Biedronka one the milk was 4.29"."""
    me = await UserFactory.create_async()
    receipt = await _biedronka(me)

    [card] = await _propose(
        db_session,
        me,
        ToolCall("change_line", {"receipt_id": str(receipt.id), "line": "mleko", "total": "4.29"}),
    )
    await _approve(db_session, me, card)

    saved = await _reloaded(db_session, receipt)
    assert (saved.total_amount, saved.status) == (Decimal("10.79"), ReceiptStatus.PARSED)


@pytest.mark.asyncio
async def test_a_line_added_and_a_line_removed_carry_the_total(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()
    receipt = await _biedronka(me)

    [added] = await _propose(
        db_session,
        me,
        ToolCall("change_line", {"receipt_id": str(receipt.id), "name": "Jabłka", "total": "7.50"}),
    )
    await _approve(db_session, me, added)
    [removed] = await _propose(
        db_session, me, ToolCall("remove_line", {"receipt_id": str(receipt.id), "line": "Chleb"})
    )
    await _approve(db_session, me, removed)

    saved = await _reloaded(db_session, receipt)
    assert saved.total_amount == Decimal("11.50")


@pytest.mark.asyncio
async def test_confirming_a_receipt_sets_its_total_to_its_lines(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()
    receipt = await _biedronka(me, total="12.00", status=ReceiptStatus.MANUAL_REVIEW)

    [card] = await _propose(
        db_session, me, ToolCall("confirm_receipt", {"receipt_id": str(receipt.id)})
    )
    await _approve(db_session, me, card)

    saved = await _reloaded(db_session, receipt)
    assert (saved.total_amount, saved.status) == (Decimal("10.50"), ReceiptStatus.PARSED)


@pytest.mark.asyncio
async def test_a_receipt_deleted_by_chat_is_gone(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()
    receipt = await _biedronka(me)

    [card] = await _propose(
        db_session, me, ToolCall("delete_receipt", {"receipt_id": str(receipt.id)})
    )
    await _approve(db_session, me, card)

    receipt_id = receipt.id
    db_session.expire_all()
    assert (await db_session.get(Receipt, receipt_id)) is None


@pytest.mark.asyncio
async def test_a_new_trip_and_a_receipt_put_on_it(db_session: AsyncSession) -> None:
    me = await UserFactory.create_async()
    receipt = await _biedronka(me)

    [trip_card] = await _propose(
        db_session,
        me,
        ToolCall("add_trip", {"name": "Kraków", "start": "2026-11-02", "end": "2026-11-04"}),
    )
    await _approve(db_session, me, trip_card)
    [placed] = await _propose(
        db_session,
        me,
        ToolCall("receipt_trip", {"receipt_id": str(receipt.id), "trip": "krakow"}),
    )
    await _approve(db_session, me, placed)

    me_id = me.id
    saved = await _reloaded(db_session, receipt)
    trip = (await db_session.execute(select(Trip).where(Trip.user_id == me_id))).scalar_one()
    assert (trip.start_date, saved.trip_id, saved.trip_manual) == (
        date(2026, 11, 2),
        trip.id,
        True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "extra"),
    [
        ("change_line", {"line": "Mleko", "total": "1"}),
        ("remove_line", {"line": "Mleko"}),
        ("confirm_receipt", {}),
        ("delete_receipt", {}),
        ("receipt_trip", {}),
    ],
)
async def test_another_users_receipt_is_never_changed_by_chat(
    db_session: AsyncSession, tool: str, extra: dict[str, str]
) -> None:
    me = await UserFactory.create_async()
    stranger = await UserFactory.create_async()
    theirs = await _biedronka(stranger, status=ReceiptStatus.MANUAL_REVIEW, total="12.00")
    toolbox = _toolbox(db_session, me)

    refused = await toolbox.check(ToolCall(tool, {"receipt_id": str(theirs.id), **extra}))
    figures = json.loads(
        await toolbox.read(ToolCall("receipt_lines", {"receipt_id": str(theirs.id)}))
    )

    assert refused is not None and "no receipt of the user's own" in refused
    assert "error" in figures


@pytest.mark.asyncio
async def test_a_shopping_trip_told_is_one_receipt_with_its_lines_categorised(
    db_session: AsyncSession,
) -> None:
    """F21.8.1: "Biedronka today: milk 4, bread 5, apples 7.50"."""
    me = await UserFactory.create_async()

    [card] = await _propose(
        db_session,
        me,
        ToolCall(
            "add_told_receipt",
            {
                "shop": "Biedronka",
                "spent_on": "2026-10-23",
                "lines": [
                    {"name": "Mleko", "amount": "4"},
                    {"name": "Chleb", "amount": "5"},
                    {"name": "Jabłka", "quantity": "2", "amount": "7.50"},
                ],
            },
        ),
    )
    card["card"]["fields"]["lines"][0]["amount"] = "4.29"
    await _approve(db_session, me, card)

    me_id = me.id
    db_session.expire_all()
    told = (
        await db_session.execute(
            select(Receipt)
            .where(Receipt.user_id == me_id)
            .options(selectinload(Receipt.line_items).selectinload(LineItem.category))
        )
    ).scalar_one()
    assert (told.channel, told.merchant_name, told.total_amount, told.status) == (
        ReceiptChannel.TOLD,
        "Biedronka",
        Decimal("16.79"),
        ReceiptStatus.PARSED,
    )
    assert {i.category.name for i in told.line_items if i.category} == {"Groceries"}


@pytest.mark.asyncio
async def test_a_price_said_of_a_one_line_receipt_corrects_its_line(
    db_session: AsyncSession,
) -> None:
    """ "The YouTube one was 59.99": a receipt of one line needs no line named."""
    me = await UserFactory.create_async()
    receipt = await ReceiptFactory.create_async(
        user_id=me.id, merchant_name="YouTube", total_amount=Decimal("60.00"), file_ids=[]
    )
    await LineItemFactory.create_async(
        receipt=receipt,
        name="YouTube Premium",
        quantity=Decimal(1),
        unit_price=Decimal("60.00"),
        total_price=Decimal("60.00"),
        position=0,
    )

    [card] = await _propose(
        db_session, me, ToolCall("change_line", {"receipt_id": str(receipt.id), "total": "59.99"})
    )
    await _approve(db_session, me, card)

    saved = await _reloaded(db_session, receipt)
    assert (card["card"]["fields"]["name"], saved.total_amount) == (
        "YouTube Premium",
        Decimal("59.99"),
    )
