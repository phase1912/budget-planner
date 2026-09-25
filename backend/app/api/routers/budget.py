from typing import Annotated

from fastapi import APIRouter, Depends, Path
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
) -> MonthSummaryResponse:
    """The caller's spend in one calendar month, by receipt date (BRD D1, D2).

    The client names the month: which month is "now" depends on the user's own
    clock, which only the browser knows (ADR-0009).
    """
    summary = await BudgetService(ReceiptRepository(session)).month_summary(
        BudgetMonth(year, month)
    )
    return MonthSummaryResponse(
        year=summary.month.year,
        month=summary.month.month,
        total=summary.total,
        receipt_count=summary.receipt_count,
        has_receipts=summary.has_receipts,
    )
