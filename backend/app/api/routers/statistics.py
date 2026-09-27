from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.periods import required_period
from app.db.session import get_db_session
from app.domain.periods import DateRange
from app.domain.statistics import CategoryStanding
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.schemas.statistics import (
    CategoryStandingResponse,
    CategoryStatisticsResponse,
    ComparisonResponse,
)
from app.services.statistics import StatisticsService

router = APIRouter(prefix="/api/v1/statistics", tags=["statistics"])


@router.get("/categories", response_model=CategoryStatisticsResponse)
async def get_category_statistics(
    period: Annotated[DateRange, Depends(required_period)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    compare: Annotated[
        bool, Query(description="Also measure each category against the previous period")
    ] = False,
) -> CategoryStatisticsResponse:
    """The caller's spend per category between two dates, ranked highest first (BRD E1-E4).

    `start` and `end` are both included, as everywhere (app/api/periods.py).
    With `compare`, each category also carries its change against the previous
    like-for-like period (E3). Only the caller's own receipts are read (N2). A
    period ending before it starts is refused with 422 rather than answered as
    an empty one.
    """
    stats = await StatisticsService(ReceiptRepository(session)).category_statistics(
        period, compare=compare
    )
    comparison = stats.comparison
    if comparison is None:
        rows = [_row(c) for c in stats.categories]
    else:
        rows = [
            _row(
                c.standing,
                previous_total=c.previous_total,
                change=c.change,
                change_percent=c.change_percent,
            )
            for c in comparison.changes
        ]
    return CategoryStatisticsResponse(
        start=stats.period.start,
        end=stats.period.end,
        total=stats.total,
        item_count=stats.item_count,
        categories=rows,
        excluded_count=stats.excluded_count,
        excluded_amount=stats.excluded_amount,
        comparison=ComparisonResponse(
            start=comparison.period.start,
            end=comparison.period.end,
            total=comparison.total,
            item_count=comparison.item_count,
            stops_mid_month=comparison.stops_mid_month,
        )
        if comparison
        else None,
    )


def _row(standing: CategoryStanding, **change: Decimal | None) -> CategoryStandingResponse:
    """One category as the API shows it, with its change when there is one."""
    return CategoryStandingResponse(
        category_id=standing.category_id,
        name=standing.name,
        total=standing.total,
        share=standing.share,
        item_count=standing.item_count,
        **change,
    )
