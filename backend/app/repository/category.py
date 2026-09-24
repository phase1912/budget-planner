import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, case, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.categories import DEFAULT_CATEGORY_ORDER, normalise_name
from app.models.category import Category
from app.models.category_rule import CategoryRule
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.repository.base import BaseRepository


@dataclass(frozen=True)
class CategoryWithStatistics:
    """A category plus what the current user has filed under it (BRD C1)."""

    id: uuid.UUID
    name: str
    is_builtin: bool
    item_count: int
    total_amount: Decimal


class CategoryRepository(BaseRepository[Category]):
    """Data access for the spending taxonomy (BRD C1, C2, C6).

    A category is either built in — `user_id IS NULL`, shared by everyone — or
    owned by one user, so the base class's ownership filter would hide exactly
    the rows every user must see. Every method here scopes to "the built-ins
    plus mine" instead, which is the only visibility rule the taxonomy has.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model_class=Category, session=session)

    def _visible_to(self, user_id: uuid.UUID) -> Select[tuple[Category]]:
        return select(Category).where(or_(Category.user_id.is_(None), Category.user_id == user_id))

    @staticmethod
    def _ordering() -> list[ColumnElement[Any]]:
        """Built-ins first in the BRD's order, then the user's own by name."""
        rank = case(
            {name: index for index, name in enumerate(DEFAULT_CATEGORY_ORDER)},
            value=Category.name,
            else_=len(DEFAULT_CATEGORY_ORDER),
        )
        return [Category.user_id.isnot(None), rank, Category.name.asc()]

    async def list_available(self, user_id: uuid.UUID) -> Sequence[Category]:
        """Every category this user may be assigned from, automatically or by hand.

        This is the set handed to the categoriser, so a category missing here can
        never be chosen — which is also what keeps one user's custom categories
        out of another user's receipts (BRD N2).
        """
        stmt = self._visible_to(user_id).order_by(*self._ordering())
        return (await self.session.execute(stmt)).scalars().all()

    async def get_available(self, category_id: uuid.UUID, user_id: uuid.UUID) -> Category | None:
        """One category this user may assign from, or None if it is not theirs to use.

        A built-in or the user's own; another user's custom category comes back
        as None, exactly like one that does not exist (BRD N2).
        """
        stmt = self._visible_to(user_id).where(Category.id == category_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_with_statistics(self, user_id: uuid.UUID) -> list[CategoryWithStatistics]:
        """The taxonomy with each category's item count and total for this user.

        The line-item join is restricted to the user's own receipts before it is
        aggregated, so a built-in category reports what *this* user filed under
        it rather than what everyone did (BRD N2). Categories with nothing in
        them still come back, at zero.
        """
        owned_receipts = select(Receipt.id).where(Receipt.user_id == user_id)

        stmt = (
            select(
                Category.id,
                Category.name,
                Category.user_id.is_(None).label("is_builtin"),
                func.count(LineItem.id).label("item_count"),
                func.coalesce(func.sum(LineItem.total_price), 0).label("total_amount"),
            )
            .outerjoin(
                LineItem,
                (LineItem.category_id == Category.id) & LineItem.receipt_id.in_(owned_receipts),
            )
            .where(or_(Category.user_id.is_(None), Category.user_id == user_id))
            .group_by(Category.id, Category.name, Category.user_id)
            .order_by(*self._ordering())
        )

        rows = (await self.session.execute(stmt)).all()
        return [
            CategoryWithStatistics(
                id=row.id,
                name=row.name,
                is_builtin=row.is_builtin,
                item_count=row.item_count,
                total_amount=Decimal(row.total_amount),
            )
            for row in rows
        ]

    async def list_rules(self, user_id: uuid.UUID) -> Sequence[CategoryRule]:
        """Every correction rule this user has made; never another user's (BRD C5, N2)."""
        stmt = select(CategoryRule).where(CategoryRule.user_id == user_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def save_rule(
        self,
        user_id: uuid.UUID,
        merchant_name: str | None,
        item_name: str,
        category_id: uuid.UUID,
    ) -> CategoryRule:
        """Remember a correction for future items, replacing any earlier one for that item (C5).

        Names are stored normalised, so "Protein Bar XL" and "protein bar xl" at
        the same merchant are one rule, and the latest choice wins.
        """
        merchant = normalise_name(merchant_name)
        item = normalise_name(item_name)
        stmt = select(CategoryRule).where(
            CategoryRule.user_id == user_id,
            CategoryRule.merchant_name == merchant,
            CategoryRule.item_name == item,
        )
        rule = (await self.session.execute(stmt)).scalar_one_or_none()
        if rule is None:
            rule = CategoryRule(user_id=user_id, merchant_name=merchant, item_name=item)
            self.session.add(rule)
        rule.category_id = category_id
        rule.created_at = datetime.now(UTC)
        await self.session.flush()
        return rule

    async def get_owned(self, category_id: uuid.UUID, user_id: uuid.UUID) -> Category | None:
        """One of the user's own categories; None for a built-in or another user's (N2)."""
        stmt = select(Category).where(Category.id == category_id, Category.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def name_taken(
        self, user_id: uuid.UUID, name: str, *, ignoring: uuid.UUID | None = None
    ) -> bool:
        """Whether a category this user can see already has this name, ignoring case (C6)."""
        stmt = self._visible_to(user_id).where(func.lower(Category.name) == name.lower())
        if ignoring is not None:
            stmt = stmt.where(Category.id != ignoring)
        return (await self.session.execute(stmt)).first() is not None

    async def create_custom(self, user_id: uuid.UUID, name: str) -> Category:
        """Store a new custom category owned by this user (C6)."""
        category = Category(user_id=user_id, name=name)
        self.session.add(category)
        await self.session.flush()
        return category

    async def move_items(
        self, user_id: uuid.UUID, source_id: uuid.UUID, target_id: uuid.UUID
    ) -> None:
        """Refile this user's items from one category to another (C7)."""
        owned_receipts = select(Receipt.id).where(Receipt.user_id == user_id)
        await self.session.execute(
            update(LineItem)
            .where(LineItem.category_id == source_id, LineItem.receipt_id.in_(owned_receipts))
            .values(category_id=target_id)
            .execution_options(synchronize_session=False)
        )

    async def move_rules(
        self, user_id: uuid.UUID, source_id: uuid.UUID, target_id: uuid.UUID
    ) -> None:
        """Point this user's correction rules at another category (C5, C7)."""
        await self.session.execute(
            update(CategoryRule)
            .where(CategoryRule.user_id == user_id, CategoryRule.category_id == source_id)
            .values(category_id=target_id)
            .execution_options(synchronize_session=False)
        )

    async def delete_rules(self, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
        """Forget this user's correction rules that file into one category (C5, C7)."""
        await self.session.execute(
            delete(CategoryRule).where(
                CategoryRule.user_id == user_id, CategoryRule.category_id == category_id
            )
        )

    async def remove(self, category: Category) -> None:
        """Delete a category row; callers move what referenced it first."""
        await self.session.delete(category)
        await self.session.flush()
