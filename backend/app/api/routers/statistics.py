from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.periods import required_period
from app.db.session import get_db_session
from app.domain.periods import DateRange
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.schemas.statistics import CategoryStatisticsResponse
from app.services.statistics import StatisticsService, statistics_response

router = APIRouter(prefix="/api/v1/statistics", tags=["statistics"])


@router.get("/categories", response_model=CategoryStatisticsResponse)
async def get_category_statistics(
    period: Annotated[DateRange, Depends(required_period)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    compare: Annotated[
        bool, Query(description="Also measure each category against the previous period")
    ] = False,
    chart: Annotated[bool, Query(description="Also return the figures as a chart")] = False,
) -> CategoryStatisticsResponse:
    """The caller's spend per category between two dates, ranked highest first (BRD E1-E6).

    `start` and `end` are both included, as everywhere (app/api/periods.py).
    With `compare`, each category also carries its change against the previous
    like-for-like period (E3); with `chart`, the figures come as a chart ready
    to draw (E6). Only the caller's own receipts are read (N2). A period ending
    before it starts is refused with 422 rather than answered as an empty one; a
    period holding no receipts says so with `receipt_count` 0 and no totals,
    rather than a report of zeroes (E5).
    """
    stats = await StatisticsService(ReceiptRepository(session)).category_statistics(
        period, compare=compare, chart=chart
    )
    return statistics_response(stats)
