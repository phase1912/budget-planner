import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.discounts import WHOLE_RECEIPT_DISCOUNT
from app.models.line_item import LineItem
from app.models.product import Product, ProductAlias
from app.models.receipt import Receipt


class ProductRepository:
    """The user's products and the lines matched to them (F16.1); every query names the user.

    Products and aliases carry `user_id`; lines are reached through their receipt's
    owner, so another user's lines are never matched, counted or moved (N2).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def aliases(self, user_id: uuid.UUID) -> Sequence[ProductAlias]:
        """Every way the user's products are printed."""
        stmt = select(ProductAlias).where(ProductAlias.user_id == user_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def unmatched_lines(self, user_id: uuid.UUID) -> list[tuple[uuid.UUID, str]]:
        """The user's purchase lines with no product yet: id and printed name.

        Discounts and zero lines are not purchases of anything, so they are left out.
        """
        stmt = (
            select(LineItem.id, LineItem.name)
            .join(Receipt, Receipt.id == LineItem.receipt_id)
            .where(
                Receipt.user_id == user_id,
                LineItem.product_id.is_(None),
                LineItem.total_price > 0,
                LineItem.name != WHOLE_RECEIPT_DISCOUNT,
            )
        )
        return [(i, n) for i, n in (await self.session.execute(stmt)).all()]

    async def lines_of(
        self, user_id: uuid.UUID, product_ids: Sequence[uuid.UUID]
    ) -> list[tuple[uuid.UUID, uuid.UUID, str]]:
        """The user's lines matched to these products: id, product id, printed name."""
        stmt = (
            select(LineItem.id, LineItem.product_id, LineItem.name)
            .join(Receipt, Receipt.id == LineItem.receipt_id)
            .where(Receipt.user_id == user_id, LineItem.product_id.in_(product_ids))
        )
        return [(i, p, n) for i, p, n in (await self.session.execute(stmt)).all()]

    async def link(self, line_ids: Sequence[uuid.UUID], product_id: uuid.UUID) -> None:
        """Match these lines to a product; the caller has checked they are the user's."""
        if line_ids:
            await self.session.execute(
                update(LineItem).where(LineItem.id.in_(line_ids)).values(product_id=product_id)
            )

    async def get(self, user_id: uuid.UUID, product_id: uuid.UUID) -> Product | None:
        """One of the user's products with its aliases, or None — another user's is none (N2)."""
        stmt = (
            select(Product)
            .options(selectinload(Product.aliases))
            .where(Product.id == product_id, Product.user_id == user_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_with_aliases(self, user_id: uuid.UUID) -> Sequence[Product]:
        """All of the user's products, each with the ways it is printed."""
        stmt = (
            select(Product).options(selectinload(Product.aliases)).where(Product.user_id == user_id)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def purchases(
        self, user_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[int, int, datetime | None, Decimal]]:
        """Per product: times bought, shops bought in, last bought, amount spent."""
        shop = func.lower(func.trim(Receipt.merchant_name))
        stmt = (
            select(
                LineItem.product_id,
                func.count(LineItem.id),
                func.count(func.distinct(shop)),
                func.max(func.coalesce(Receipt.transaction_date, Receipt.created_at)),
                func.sum(LineItem.total_price),
            )
            .join(Receipt, Receipt.id == LineItem.receipt_id)
            .where(Receipt.user_id == user_id, LineItem.product_id.is_not(None))
            .group_by(LineItem.product_id)
        )
        return {
            product_id: (times, shops, last, spent or Decimal(0))
            for product_id, times, shops, last, spent in (await self.session.execute(stmt)).all()
        }
