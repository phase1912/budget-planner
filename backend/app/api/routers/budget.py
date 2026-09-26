from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.domain.budget import BudgetMonth
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.schemas.budget import MonthSummaryResponse
from app.services.budget import BudgetService

router = APIRouter(prefix="/api/v1/budget", tags=["budget"])


@router.get("/months/{year}/{month}", response_model=MonthSummaryResponse)
async def get_month_summary(
    year: Annotated[int, Path(ge=1970, le=9999)],
    month: Annotated[int, Path(ge=1, le=12)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    today: Annotated[date | None, Query()] = None,
) -> MonthSummaryResponse:
    """The caller's spend in one calendar month, and what is held out of it (BRD D1-D3).

    The client names the month and passes its own `today`: whether a month is
    still running depends on the user's clock, which only the browser knows
    (ADR-0009). Without it the server's UTC date stands in.
    """
    summary = await BudgetService(ReceiptRepository(session)).month_summary(
        BudgetMonth(year, month), today or datetime.now(UTC).date()
    )
    return MonthSummaryResponse(
        year=summary.month.year,
        month=summary.month.month,
        total=summary.total,
        receipt_count=summary.receipt_count,
        has_receipts=summary.has_receipts,
        excluded_count=summary.excluded_count,
        excluded_amount=summary.excluded_amount,
        is_complete=summary.progress.is_complete,
        days_elapsed=summary.progress.days_elapsed,
        days_in_month=summary.progress.days,
    )
