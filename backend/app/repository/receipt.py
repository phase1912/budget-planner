import typing
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.receipt import Receipt
from app.repository.base import BaseRepository


class ReceiptRepository(BaseRepository[Receipt]):
    """Repository for managing receipts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model_class=Receipt, session=session)

    def bypass_ownership(self) -> "ReceiptRepository":
        """Skip user-ownership filtering for system-level operations."""
        super().bypass_ownership()
        return self

    async def get_with_items(self, id: uuid.UUID) -> Receipt | None:
        """Fetch a receipt including its line items."""
        stmt = select(self.model_class).where(self.model_class.id == id)
        from app.models.line_item import LineItem

        stmt = stmt.options(joinedload(self.model_class.line_items).joinedload(LineItem.category))
        stmt = self._apply_ownership(stmt)
        return (await self.session.execute(stmt)).unique().scalar_one_or_none()

    async def list_paginated(self, skip: int, limit: int) -> tuple[typing.Sequence[Receipt], int]:
        """Return a page of receipts and the total count."""
        from sqlalchemy import func

        # Count query
        count_stmt = select(func.count()).select_from(self.model_class)
        count_stmt = self._apply_ownership(count_stmt)
        total = await self.session.scalar(count_stmt) or 0

        # Items query
        stmt = select(self.model_class)
        stmt = self._apply_ownership(stmt)
        stmt = stmt.order_by(
            self.model_class.transaction_date.desc().nulls_last(),
            self.model_class.created_at.desc(),
        )
        stmt = stmt.offset(skip).limit(limit)

        stmt = stmt.options(joinedload(self.model_class.line_items))

        result = await self.session.execute(stmt)
        items = result.unique().scalars().all()
        return items, total

    async def exists_for_user(self, user_id: uuid.UUID) -> bool:
        """Check if any receipts exist for the given user."""
        from sqlalchemy import text
        from sqlalchemy.exc import ProgrammingError

        try:
            async with self.session.begin_nested():
                stmt = text("SELECT 1 FROM receipts WHERE user_id = :user_id LIMIT 1")
                result = await self.session.execute(stmt, {"user_id": user_id})
                return result.scalar() is not None
        except ProgrammingError:
            return False

    async def has_duplicate(
        self,
        user_id: uuid.UUID,
        merchant_name: str | None,
        transaction_date_str: str | None,
        total_amount_str: str | None,
    ) -> bool:
        """Check if a receipt with the same merchant, date, and total exists for the user."""
        if not merchant_name or not transaction_date_str or not total_amount_str:
            return False

        import contextlib
        from decimal import Decimal

        from sqlalchemy import Date, cast

        total_amount = None
        with contextlib.suppress(Exception):
            total_amount = Decimal(str(total_amount_str).replace(",", "."))

        if total_amount is None:
            return False

        stmt = select(self.model_class).where(
            self.model_class.user_id == user_id,
            self.model_class.merchant_name == merchant_name,
            self.model_class.total_amount == total_amount,
        )

        try:
            import datetime

            dt = datetime.datetime.strptime(transaction_date_str, "%Y-%m-%d").date()
            stmt = stmt.where(cast(self.model_class.transaction_date, Date) == dt)
        except ValueError:
            return False

        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    def create_from_extraction(
        self,
        user_id: uuid.UUID,
        file_ids: list[str],
        extraction: dict[str, typing.Any],
        parser_version: str,
    ) -> Receipt:
        """Instantiate and save a Receipt and its LineItems from a parser extraction."""
        import contextlib
        import datetime
        from decimal import Decimal

        from app.models.line_item import LineItem
        from app.models.receipt import ReceiptStatus

        receipt_status = (
            ReceiptStatus.MANUAL_REVIEW
            if extraction.get("requires_manual_review")
            else ReceiptStatus.PARSED
        )

        dt = None
        t_date = extraction.get("transaction_date")
        if t_date:
            try:
                d = datetime.datetime.strptime(t_date, "%Y-%m-%d")
                t_time = extraction.get("transaction_time")
                if t_time:
                    t = datetime.datetime.strptime(t_time, "%H:%M").time()
                    d = datetime.datetime.combine(d.date(), t)
                dt = d.replace(tzinfo=datetime.UTC)
            except ValueError:
                pass

        total_amt = None
        rt = extraction.get("receipt_total")
        if rt:
            with contextlib.suppress(Exception):
                total_amt = Decimal(str(rt).replace(",", "."))

        receipt = Receipt(
            user_id=user_id,
            merchant_name=extraction.get("merchant_name"),
            transaction_date=dt,
            total_amount=total_amt,
            status=receipt_status,
            file_ids=file_ids,
            parser_version=parser_version,
        )

        items_data = extraction.get("line_items", [])
        if not isinstance(items_data, list):
            items_data = []

        line_items = []
        for item_data in items_data:
            if not isinstance(item_data, dict):
                continue
            try:
                qty = Decimal(str(item_data.get("quantity", "1")).replace(",", "."))
                up = Decimal(str(item_data.get("unit_price", "0")).replace(",", "."))
                tp = Decimal(str(item_data.get("total_price", "0")).replace(",", "."))
            except Exception:
                qty, up, tp = Decimal("1"), Decimal("0"), Decimal("0")

            line_items.append(
                LineItem(
                    name=item_data.get("name", "Unknown Item"),
                    quantity=qty,
                    unit_price=up,
                    total_price=tp,
                )
            )

        receipt.line_items = line_items
        self.add(receipt)
        return receipt
