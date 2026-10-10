"""What a household spends, added up across its members (F12.5, ADR-0017)."""

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.periods import DateRange
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.receipt import Receipt, ReceiptStatus
from app.repository.receipt import _within


@dataclass(frozen=True)
class MemberSpend:
    """One member's spend over a period, their shared and private receipts apart."""

    user_id: uuid.UUID
    shared_total: Decimal
    shared_count: int
    private_total: Decimal
    private_count: int


@dataclass(frozen=True)
class SharedCategorySpend:
    """One category's share of a household's shared spend; `owner_id` set for a custom one.

    Built-in categories are everyone's and add up across members; a member's own
    category stays theirs, so two members' "Pets" are two rows.
    """

    category_id: uuid.UUID | None
    name: str | None
    owner_id: uuid.UUID | None
    item_count: int
    total: Decimal


class HouseholdSpendRepository:
    """Sums over the receipts of a set of household members, never their details.

    Counts what the personal figures count — line items on parsed receipts, filed by
    printed date or else upload date (D1-D3) — so a household's month is exactly the
    sum of its members' months. Private receipts are added in as money only.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_member(
        self, period: DateRange, member_ids: Collection[uuid.UUID]
    ) -> list[MemberSpend]:
        """Each member's parsed spend over `period`, shared and private apart."""
        stmt = (
            select(
                Receipt.user_id,
                Receipt.is_private,
                func.count(func.distinct(Receipt.id)),
                func.coalesce(func.sum(LineItem.total_price), 0),
            )
            .outerjoin(LineItem, LineItem.receipt_id == Receipt.id)
            .where(
                Receipt.user_id.in_(member_ids),
                Receipt.status == ReceiptStatus.PARSED,
                _within(period),
            )
            .group_by(Receipt.user_id, Receipt.is_private)
        )
        sums: dict[uuid.UUID, dict[bool, tuple[int, Decimal]]] = {}
        for user_id, private, count, total in (await self.session.execute(stmt)).all():
            sums.setdefault(user_id, {})[private] = (int(count), Decimal(total))
        none = (0, Decimal(0))
        return [
            MemberSpend(
                user_id=member,
                shared_total=sums.get(member, {}).get(False, none)[1],
                shared_count=sums.get(member, {}).get(False, none)[0],
                private_total=sums.get(member, {}).get(True, none)[1],
                private_count=sums.get(member, {}).get(True, none)[0],
            )
            for member in member_ids
        ]

    async def under_review(
        self, period: DateRange, member_ids: Collection[uuid.UUID]
    ) -> tuple[int, Decimal]:
        """How many of the members' receipts over `period` await review, and their value (D3)."""
        held = select(Receipt.id).where(
            Receipt.user_id.in_(member_ids),
            Receipt.status == ReceiptStatus.MANUAL_REVIEW,
            _within(period),
        )
        count = await self.session.scalar(select(func.count()).select_from(held.subquery()))
        value = await self.session.scalar(
            select(func.coalesce(func.sum(LineItem.total_price), 0)).where(
                LineItem.receipt_id.in_(held)
            )
        )
        return int(count or 0), Decimal(value or 0)

    async def shared_categories(
        self, period: DateRange, member_ids: Collection[uuid.UUID]
    ) -> list[SharedCategorySpend]:
        """Spend per category over the members' shared receipts, highest first (E1).

        Private receipts are left out entirely: their categories would say what they were.
        """
        stmt = (
            select(
                Category.id,
                Category.name,
                Category.user_id,
                func.count(LineItem.id),
                func.coalesce(func.sum(LineItem.total_price), 0),
            )
            .select_from(LineItem)
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .outerjoin(Category, LineItem.category_id == Category.id)
            .where(
                Receipt.user_id.in_(member_ids),
                Receipt.status == ReceiptStatus.PARSED,
                Receipt.is_private.is_(False),
                _within(period),
            )
            .group_by(Category.id, Category.name, Category.user_id)
            .order_by(func.sum(LineItem.total_price).desc(), Category.name)
        )
        return [
            SharedCategorySpend(category_id, name, owner_id, int(count), Decimal(total))
            for category_id, name, owner_id, count, total in (
                await self.session.execute(stmt)
            ).all()
        ]
