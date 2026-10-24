"""The service's own analytics (F17.3)."""

from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import rate_limit
from app.api.dependencies import get_admin_user
from app.api.periods import required_period
from app.api.rate_limit import limiter
from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.activity import DIRECT, is_bot, system_family, visit_source
from app.domain.periods import DateRange
from app.models.user import User
from app.schemas.analytics import Count, DayFiguresRead, PageViewRequest, UsageReportRead
from app.services.activity import ActivityService, UsageReportService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.post("/views", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(rate_limit.PAGE_VIEWS)
async def count_view(
    request: Request,
    body: PageViewRequest,
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> Response:
    """Count one view of a public page (F17.3.2); a crawler or another path is not counted.

    Nothing about the visitor is kept: not the IP, not the full referrer, not the
    User-Agent — only the page, the referring domain or campaign, the platform, the
    system's family and the day. Always 204, so it tells a caller nothing.
    """
    user_agent = request.headers.get("user-agent")
    if not is_bot(user_agent):
        own = urlparse(get_settings().link_base).hostname or ""
        # A later page of the same visit came from our own pages, whatever it sends.
        source = visit_source(body.referrer, body.utm_source, own) if body.entry else DIRECT
        await ActivityService(session).count_view(
            body.page,
            source,
            datetime.now(UTC).date(),
            entry=body.entry,
            platform=body.platform,
            # Only the family is kept, never the header (F17.3.4).
            system=system_family(user_agent),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/report", response_model=UsageReportRead)
async def usage_report(
    _admin: Annotated[User, Depends(get_admin_user)],
    period: Annotated[DateRange, Depends(required_period)],
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> UsageReportRead:
    """The admin dashboard's figures for a period (F17.3.3); 403 for anyone but an admin."""
    report = await UsageReportService(session, get_settings().admin_emails).report(period)
    return UsageReportRead(
        start=report.period.start,
        end=report.period.end,
        visits=report.visits,
        page_views=report.page_views,
        views_by_page=[Count(name=n, count=c) for n, c in report.views_by_page],
        visits_by_source=[Count(name=n, count=c) for n, c in report.visits_by_source],
        visits_by_platform=[Count(name=n, count=c) for n, c in report.visits_by_platform],
        visits_by_system=[Count(name=n, count=c) for n, c in report.visits_by_system],
        sign_ups=report.sign_ups,
        confirmed=report.confirmed,
        with_a_receipt=report.with_a_receipt,
        uploads=report.uploads,
        receipts_read=report.receipts_read,
        active_week=report.active_week,
        active_month=report.active_month,
        returning=report.returning,
        days=[DayFiguresRead(**vars(day)) for day in report.days],
    )
