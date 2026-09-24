import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.categories import DEFAULT_CATEGORY_ORDER
from app.models.category import Category
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
