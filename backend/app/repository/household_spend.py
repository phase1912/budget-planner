"""What a household spends, added up across its members (F12.5, ADR-0017)."""

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.family_lines import FamilyLine
from app.domain.periods import DateRange
from app.domain.trips import TripKind
from app.models.category import Category
from app.models.income import Income
from app.models.income_source import IncomeSource
from app.models.line_item import LineItem
from app.models.product import Product
from app.models.receipt import Receipt, ReceiptStatus
from app.models.regular_expense import RegularExpense
from app.repository.receipt import (
    _purchased,
    _within,
    counted_in_budget,
    on_trip,
    purchase_day,
)


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
                func.coalesce(func.sum(LineItem.paid), 0),
            )
            .outerjoin(LineItem, LineItem.receipt_id == Receipt.id)
            .where(
                Receipt.user_id.in_(member_ids),
                counted_in_budget(),
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
            ~on_trip(TripKind.BUSINESS),
            _within(period),
        )
        count = await self.session.scalar(select(func.count()).select_from(held.subquery()))
        value = await self.session.scalar(
            select(func.coalesce(func.sum(LineItem.paid), 0)).where(LineItem.receipt_id.in_(held))
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
                func.coalesce(func.sum(LineItem.paid), 0),
            )
            .select_from(LineItem)
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .outerjoin(Category, LineItem.category_id == Category.id)
            .where(
                Receipt.user_id.in_(member_ids),
                counted_in_budget(),
                Receipt.is_private.is_(False),
                _within(period),
            )
            .group_by(Category.id, Category.name, Category.user_id)
            .order_by(func.sum(LineItem.paid).desc(), Category.name)
        )
        return [
            SharedCategorySpend(category_id, name, owner_id, int(count), Decimal(total))
            for category_id, name, owner_id, count, total in (
                await self.session.execute(stmt)
            ).all()
        ]

    async def daily_by_member(
        self, period: DateRange, member_ids: Collection[uuid.UUID], viewer_id: uuid.UUID
    ) -> dict[tuple[date, uuid.UUID], Decimal]:
        """Each member's spend on each day of `period` that had any, as the viewer may see it.

        A shared receipt counts on its day for its owner. A private one counts by day only
        for the viewer's own: another member's has no date in the household (ADR-0017).
        Days are taken in UTC, as the personal daily figures are, so they add up alike.
        """
        day = func.date(func.timezone("UTC", _purchased()))
        stmt = (
            select(day, Receipt.user_id, func.coalesce(func.sum(LineItem.paid), 0))
            .select_from(LineItem)
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .where(
                Receipt.user_id.in_(member_ids),
                counted_in_budget(),
                _within(period),
                or_(Receipt.is_private.is_(False), Receipt.user_id == viewer_id),
            )
            .group_by(day, Receipt.user_id)
        )
        return {
            (spent_on, user_id): Decimal(total)
            for spent_on, user_id, total in (await self.session.execute(stmt)).all()
        }

    async def category_members(
        self, period: DateRange, member_ids: Collection[uuid.UUID]
    ) -> dict[uuid.UUID | None, dict[uuid.UUID, Decimal]]:
        """Each shared category's spend split by the member who bought it (F12.9).

        Shared receipts only, as `shared_categories`: a private receipt's category would
        say what it was (ADR-0017).
        """
        stmt = (
            select(LineItem.category_id, Receipt.user_id, func.coalesce(func.sum(LineItem.paid), 0))
            .select_from(LineItem)
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .where(
                Receipt.user_id.in_(member_ids),
                counted_in_budget(),
                Receipt.is_private.is_(False),
                _within(period),
            )
            .group_by(LineItem.category_id, Receipt.user_id)
        )
        split: dict[uuid.UUID | None, dict[uuid.UUID, Decimal]] = {}
        for category_id, user_id, total in (await self.session.execute(stmt)).all():
            split.setdefault(category_id, {})[user_id] = Decimal(total)
        return split

    async def shared_money(
        self, household_id: uuid.UUID, period: DateRange
    ) -> tuple[list[Income], list[IncomeSource], list[RegularExpense]]:
        """What the household shares (F12.8) that may count in `period`: income entries of it,
        and the regular incomes and bills not ended before it starts. The caller applies the
        recurring rules to say which run in the month.
        """
        entries = await self.session.execute(
            select(Income).where(
                Income.household_id == household_id,
                Income.received_on >= period.start,
                Income.received_on <= period.end,
            )
        )
        sources = await self.session.execute(
            select(IncomeSource).where(
                IncomeSource.household_id == household_id,
                or_(IncomeSource.ends_on.is_(None), IncomeSource.ends_on >= period.start),
            )
        )
        bills = await self.session.execute(
            select(RegularExpense).where(
                RegularExpense.household_id == household_id,
                or_(RegularExpense.ends_on.is_(None), RegularExpense.ends_on >= period.start),
            )
        )
        return (
            list(entries.scalars().all()),
            list(sources.scalars().all()),
            list(bills.scalars().all()),
        )

    async def shared_lines(
        self,
        period: DateRange,
        member_ids: Collection[uuid.UUID],
        viewer_id: uuid.UUID | None = None,
    ) -> list[FamilyLine]:
        """Every line of the members' shared receipts over `period`, as the month counts
        them (F12.11). Private receipts are left out entirely: their lines say what and
        when (ADR-0017) — except the viewer's own, which advice for the viewer may use.
        A line is named by its owner's product where it has one, so a
        product printed differently by each shop is one name.
        """
        stmt = (
            select(
                Receipt.user_id,
                purchase_day(),
                func.coalesce(Product.name, LineItem.name),
                Receipt.merchant_name,
                LineItem.unit_price,
                LineItem.quantity,
                LineItem.paid,
            )
            .join(Receipt, LineItem.receipt_id == Receipt.id)
            .outerjoin(Product, LineItem.product_id == Product.id)
            .where(
                Receipt.user_id.in_(member_ids),
                counted_in_budget(),
                or_(Receipt.is_private.is_(False), Receipt.user_id == viewer_id),
                _within(period),
            )
        )
        return [
            FamilyLine(
                member_id=user_id,
                day=day,
                name=name,
                shop=shop,
                unit_price=Decimal(unit_price or 0),
                quantity=Decimal(quantity or 1),
                paid=Decimal(paid or 0),
            )
            for user_id, day, name, shop, unit_price, quantity, paid in (
                await self.session.execute(stmt)
            ).all()
        ]
