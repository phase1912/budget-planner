from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.periods import required_period
from app.db.session import get_db_session
from app.domain.daily_spend import daily_spend
from app.domain.periods import DateRange
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.schemas.reading_accuracy import ReadingAccuracyResponse
from app.schemas.statistics import CategoryStatisticsResponse, DailySpendResponse
from app.services.income import IncomeService
from app.services.reading_accuracy import reading_accuracy
from app.services.statistics import StatisticsService, statistics_response

router = APIRouter(prefix="/api/v1/statistics", tags=["statistics"])


@router.get("/categories", response_model=CategoryStatisticsResponse)
async def get_category_statistics(
    period: Annotated[DateRange, Depends(required_period)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
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
    bills = await IncomeService(session).bills_between(period.start, period.end)
    return statistics_response(stats).model_copy(update={"bills_total": bills})


@router.get("/daily", response_model=DailySpendResponse)
async def get_daily_spend(
    period: Annotated[DateRange, Depends(required_period)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
    today: Annotated[
        date | None, Query(description="The caller's own date; the average counts days to it")
    ] = None,
) -> DailySpendResponse:
    """The caller's spending on each day between two dates, both included (F23.4).

    Counted as the month's figure is (domain model invariant 4): what was paid, on
    `parsed` receipts, by printed date. Every day is listed, a quiet one as zero; only the
    caller's own receipts are read (N2).
    """
    totals = await ReceiptRepository(session).daily_totals(period)
    spend = daily_spend(period, totals, today or datetime.now(UTC).date())
    return DailySpendResponse.model_validate(asdict(spend))


@router.get("/reading-accuracy", response_model=ReadingAccuracyResponse)
async def get_reading_accuracy(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
    months: Annotated[int, Query(ge=1, le=12, description="How many months back")] = 6,
) -> ReadingAccuracyResponse:
    """How often the caller's receipts needed correcting after reading (F15.4).

    Counts receipts read in the last `months` months — the share the user had to correct,
    the shops behind most corrections, and the month-by-month trend. Only the caller's
    own receipts (N2).
    """
    report = await reading_accuracy(
        ReceiptRepository(session), current_user.id, datetime.now(UTC).date(), months
    )
    return ReadingAccuracyResponse.model_validate(asdict(report))
