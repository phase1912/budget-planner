from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.periods import required_period
from app.db.session import get_db_session
from app.domain.periods import DateRange
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.schemas.statistics import CategoryStandingResponse, CategoryStatisticsResponse
from app.services.statistics import StatisticsService

router = APIRouter(prefix="/api/v1/statistics", tags=["statistics"])


@router.get("/categories", response_model=CategoryStatisticsResponse)
async def get_category_statistics(
    period: Annotated[DateRange, Depends(required_period)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategoryStatisticsResponse:
    """The caller's spend per category between two dates, ranked highest first (BRD E1, E2, E4).

    `start` and `end` are both included, as everywhere (app/api/periods.py).
    Only the caller's own receipts are read (N2). A period ending before it
    starts is refused with 422 rather than answered as an empty one.
    """
    stats = await StatisticsService(ReceiptRepository(session)).category_statistics(period)
    return CategoryStatisticsResponse(
        start=stats.period.start,
        end=stats.period.end,
        total=stats.total,
        item_count=stats.item_count,
        categories=[
            CategoryStandingResponse(
                category_id=c.category_id,
                name=c.name,
                total=c.total,
                share=c.share,
                item_count=c.item_count,
            )
            for c in stats.categories
        ],
        excluded_count=stats.excluded_count,
        excluded_amount=stats.excluded_amount,
    )
