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
