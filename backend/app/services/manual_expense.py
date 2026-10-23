"""Expenses the user types in because there was no receipt (F20.5).

A tour paid in cash, a tip, a parking meter: the money was spent, and leaving it out
would make the month, a trip and its settlement wrong. Such an expense is stored as a
receipt of one line with the `manual` channel, so every figure that counts receipts
counts it — the month and its limit, statistics, goals, a trip by its date, a trip's
kinds — and nothing that reads receipts has to know about it. A foreign one is
converted like a read receipt (ADR-0016).
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import NotFoundError
from app.domain.activity import ActivityKind
from app.domain.trips import ExpenseKind
from app.models.receipt import Receipt, ReceiptChannel
from app.models.user import User
from app.ports.categorisation import ItemCategoriserPort
from app.ports.exchange_rates import ExchangeRatePort
from app.repository.category import CategoryRepository
from app.repository.receipt import ReceiptRepository
from app.services.activity import ActivityService
from app.services.receipt import ReceiptService
from app.services.trip import TripService


@dataclass(frozen=True)
class ManualExpense:
    """An expense without a receipt, as the user describes it.

    `currency` None means the account's. `trip_chosen` says the user picked where it goes
    — into `trip_id`, or into no trip when that is None — rather than leaving it to the date.
    """

    description: str
    spent_on: date
    amount: Decimal
    currency: str | None
    category_id: uuid.UUID
    kind: ExpenseKind | None = None
    trip_chosen: bool = False
    trip_id: uuid.UUID | None = None


async def record_expense(
    session: AsyncSession, user: User, expense: ManualExpense, rates: ExchangeRatePort | None
) -> Receipt:
    """Store an expense without a receipt as a one-line receipt of the `manual` channel.

    The category is the user's, kept over any later automatic pass (C4); a kind given is
    the user's choice (F20.2). Raises NotFoundError for a category or trip that is not
    one the user may use (N2).
    """
    if await CategoryRepository(session).get_available(expense.category_id, user.id) is None:
        raise NotFoundError("Category not found")
    amount = str(expense.amount)
    extraction = {
        "merchant_name": expense.description.strip(),
        "transaction_date": expense.spent_on.isoformat(),
        "receipt_total": amount,
        "currency": expense.currency or user.currency,
        "items_sum_matches_total": True,
        "line_items": [
            {
                "name": expense.description.strip(),
                "quantity": "1",
                "unit_price": amount,
                "total_price": amount,
                "category_id": str(expense.category_id),
                "category_confidence": 100,
            }
        ],
    }
    converted = await ReceiptService(exchange_rates=rates).convert_for_account(
        session, extraction, user.currency
    )
    receipt = ReceiptRepository(session).create_from_extraction(
        user_id=user.id,
        file_ids=[],
        extraction=converted,
        parser_version="manual",
        channel=ReceiptChannel.MANUAL,
    )
    ActivityService(session).record(user.id, ActivityKind.RECEIPT_STORED)
    for item in receipt.line_items:
        item.is_category_manual = True
    receipt.expense_kind_chosen = expense.kind
    if expense.trip_chosen:
        await TripService(session).place_new(user.id, receipt, expense.trip_id)
    await session.flush()
    return receipt


@dataclass(frozen=True)
class ToldLine:
    """One line of a receipt told in the chat: what, how many, and what it cost in all."""

    name: str
    quantity: Decimal
    amount: Decimal


@dataclass(frozen=True)
class ToldReceipt:
    """A shopping trip said or typed in the chat (F21.8.1); `currency` None is the account's."""

    shop: str
    spent_on: date
    lines: list[ToldLine]
    currency: str | None = None


async def record_told_receipt(
    session: AsyncSession,
    user: User,
    told: ToldReceipt,
    rates: ExchangeRatePort | None,
    categoriser: ItemCategoriserPort | None,
) -> Receipt:
    """Store a told receipt as a receipt of the shop with the `told` channel, its lines
    categorised as a read receipt's are — the user's rules first, then the categoriser,
    Uncategorized when unsure (C1-C5) — and converted like one when foreign (ADR-0016).

    Its total is what its lines add up to, so it always counts in the month (D3).
    """
    total = sum((line.amount for line in told.lines), Decimal(0))
    extraction: dict[str, object] = {
        "merchant_name": told.shop.strip(),
        "transaction_date": told.spent_on.isoformat(),
        "receipt_total": str(total),
        "currency": told.currency or user.currency,
        "items_sum_matches_total": True,
        "line_items": [
            {
                "name": line.name.strip(),
                "quantity": str(line.quantity),
                "unit_price": str((line.amount / line.quantity).quantize(Decimal("0.01"))),
                "total_price": str(line.amount),
            }
            for line in told.lines
        ],
    }
    categories = CategoryRepository(session)
    await ReceiptService(categoriser_port=categoriser).categorise_extraction(
        extraction,
        await categories.list_available(user.id),
        await categories.list_rules(user.id),
    )
    converted = await ReceiptService(exchange_rates=rates).convert_for_account(
        session, extraction, user.currency
    )
    receipt = ReceiptRepository(session).create_from_extraction(
        user_id=user.id,
        file_ids=[],
        extraction=converted,
        parser_version="told",
        channel=ReceiptChannel.TOLD,
    )
    ActivityService(session).record(user.id, ActivityKind.RECEIPT_STORED)
    await session.flush()
    return receipt
