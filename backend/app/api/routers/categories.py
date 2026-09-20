from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.category import Category
from app.models.line_item import LineItem
from app.models.receipt import Receipt
from app.models.user import User
from app.schemas.category import CategoryOut

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[CategoryOut]:
    """List all categories (built-in and custom) with aggregated statistics.

    Statistics (item_count and total_amount) are calculated only over the
    current user's line items.
    """
    # We join LineItem on Category, but restrict the LineItem side to the user's
    # receipts so we don't accidentally count another user's items for built-in
    # categories.
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
            (LineItem.category_id == Category.id)
            & LineItem.receipt_id.in_(select(Receipt.id).where(Receipt.user_id == current_user.id)),
        )
        .where(or_(Category.user_id.is_(None), Category.user_id == current_user.id))
        .group_by(Category.id, Category.name, Category.user_id)
        .order_by(Category.user_id.isnot(None), Category.name)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        CategoryOut(
            id=row.id,
            name=row.name,
            is_builtin=row.is_builtin,
            item_count=row.item_count,
            total_amount=row.total_amount,
        )
        for row in rows
    ]
