from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.domain.budget import BudgetMonth
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.repository.snapshot import MonthlySnapshotRepository
from app.schemas.budget import MonthDashboardResponse, MonthSummaryResponse
from app.schemas.receipt import CategorySpendResponse, ReceiptResponse
from app.services.budget import BudgetService, MonthSummary
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/api/v1/budget", tags=["budget"])


@router.get("/months/{year}/{month}", response_model=MonthSummaryResponse)
async def get_month_summary(
    year: Annotated[int, Path(ge=1970, le=9999)],
    month: Annotated[int, Path(ge=1, le=12)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    today: Annotated[date | None, Query()] = None,
) -> MonthSummaryResponse:
    """The caller's spend in one calendar month, and what is held out of it (BRD D1-D5).

    The client names the month and passes its own `today`: whether a month is
    still running depends on the user's clock, which only the browser knows
    (ADR-0009). Without it the server's UTC date stands in. A month that is over
    is served from its snapshot, taken on this first look (ADR-0010). Where the
    caller has set a monthly limit, the figure comes measured against it (D7).
    """
    now = datetime.now(UTC)
    service = BudgetService(ReceiptRepository(session), MonthlySnapshotRepository(session))
    summary = await service.month_summary(
        BudgetMonth(year, month),
        today or now.date(),
        user_id=current_user.id,
        now=now,
        limit=current_user.budget_limit,
    )
    return _month_response(summary)


@router.get("/months/{year}/{month}/dashboard", response_model=MonthDashboardResponse)
async def get_month_dashboard(
    year: Annotated[int, Path(ge=1970, le=9999)],
    month: Annotated[int, Path(ge=1, le=12)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    today: Annotated[date | None, Query()] = None,
) -> MonthDashboardResponse:
    """The landing view for one month in one round trip (F6.7, BRD D1, D4, D7).

    The month's figure as `/months/{year}/{month}` gives it, where it went by
    category, and its receipts column: the newest of a running month, the
    biggest of a finished one. `today` is the user's own date, as there.
    """
    now = datetime.now(UTC)
    receipts = ReceiptRepository(session)
    service = DashboardService(
        BudgetService(receipts, MonthlySnapshotRepository(session)), receipts
    )
    dashboard = await service.month(
        BudgetMonth(year, month),
        today or now.date(),
        user_id=current_user.id,
        now=now,
        limit=current_user.budget_limit,
    )
    return MonthDashboardResponse(
        summary=_month_response(dashboard.summary),
        categories=[
            CategorySpendResponse(
                category_id=c.category_id,
                name=c.name,
                item_count=c.item_count,
                total_amount=c.total,
            )
            for c in dashboard.categories
        ],
        receipts=[ReceiptResponse.model_validate(r) for r in dashboard.receipts],
        receipts_in_month=dashboard.receipts_in_month,
    )


def _month_response(summary: MonthSummary) -> MonthSummaryResponse:
    """The month as the API shows it, from the service's figure."""
    usage = summary.limit
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
        finalised_at=summary.finalised_at,
        budget_limit=usage.limit if usage else None,
        limit_percent=usage.percent if usage else None,
        limit_remaining=usage.remaining if usage else None,
    )
