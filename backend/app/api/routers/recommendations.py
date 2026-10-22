import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.advice_generation_agent import AdviceGenerationAdapter
from app.agent.factory import agent_from_settings
from app.api import rate_limit
from app.api.dependencies import get_current_user, get_quota_service
from app.api.rate_limit import limiter
from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.goal_analysis import ANALYSIS_MONTHS
from app.models.recommendation import Recommendation
from app.models.user import User
from app.ports.advice_generation import AdviceGeneratorPort
from app.schemas.recommendation import (
    AdviceReadinessRead,
    GoalProgressRead,
    RecommendationFeedbackUpdate,
    RecommendationRead,
)
from app.services.advice import AdviceService, build_advice_service
from app.services.goal_progress import GoalProgressService
from app.services.quota import QuotaService

router = APIRouter(prefix="/api/v1", tags=["advice"])


def get_advice_generator() -> AdviceGeneratorPort:
    """Provide the advice generator port; tests override this to stay off the network."""
    return AdviceGenerationAdapter(agent_from_settings())


def get_advice_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    generator: Annotated[AdviceGeneratorPort, Depends(get_advice_generator)],
) -> AdviceService:
    """The advice service bound to the request's session."""
    settings = get_settings()
    return build_advice_service(
        session,
        generator,
        required_receipts=settings.min_receipts_for_advice,
        required_days=settings.min_history_days_for_advice,
    )


Service = Annotated[AdviceService, Depends(get_advice_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/recommendations", response_model=list[RecommendationRead])
async def list_recommendations(
    current_user: CurrentUser, service: Service
) -> Sequence[Recommendation]:
    """Every goal's current advice for the Goals screen, in one request (BRD F3)."""
    return await service.list_mine()


@router.get("/advice/readiness", response_model=AdviceReadinessRead)
async def advice_readiness(current_user: CurrentUser, service: Service) -> AdviceReadinessRead:
    """Whether the caller has enough history for advice yet, and how close (BRD F5)."""
    readiness = await service.readiness(datetime.now(UTC).date())
    return AdviceReadinessRead(
        ready=readiness.ready,
        receipts=readiness.receipts,
        required_receipts=readiness.required_receipts,
        history_days=readiness.history_days,
        required_days=readiness.required_days,
        progress=readiness.progress,
        analysis_months=ANALYSIS_MONTHS,
    )


@router.get("/goals/progress", response_model=list[GoalProgressRead])
async def goal_progress(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[GoalProgressRead]:
    """Where each of the caller's goals stands (BRD F6, F7 — F8.11.2): a monthly cap's
    pace, a savings goal's money against its date, a lifestyle goal's month.

    This is also how an at-risk warning reaches the user: worked out on every look, so it
    is never stale, and waiting for them without their asking. Only the caller's own (N2).
    """
    today = datetime.now(UTC).date()
    return [
        GoalProgressRead.of(standing, today)
        for standing in await GoalProgressService(session).standings(today)
    ]


@router.post("/goals/{goal_id}/warning/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_warning(goal_id: uuid.UUID, current_user: CurrentUser, service: Service) -> None:
    """Set a goal's at-risk warning aside until next month (BRD F7).

    Another user's goal is not found (N2).
    """
    await service.dismiss_warning(goal_id, datetime.now(UTC).date())


@router.post(
    "/goals/{goal_id}/recommendations",
    response_model=list[RecommendationRead],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(rate_limit.ADVICE)
async def advise_on_goal(
    request: Request,
    goal_id: uuid.UUID,
    current_user: CurrentUser,
    service: Service,
    quota: Annotated[QuotaService, Depends(get_quota_service)],
) -> Sequence[Recommendation]:
    """Fresh advice on one goal, replacing its earlier advice (BRD F2, F3).

    Each ask is a model call, so it is limited per client IP (F10.6.3) and paid from the
    AI credits (F21.9): 429 quota_exceeded when they are spent.

    Another user's goal is not found (N2); too little history is 422 with the code
    `insufficient_data` (F5); a model that gives no answer is 503.
    """
    await quota.ensure_can_talk(current_user, datetime.now(UTC))
    return await service.advise(
        goal_id,
        as_of=datetime.now(UTC).date(),
        currency=current_user.currency,
        language=current_user.language or "en",
    )


@router.patch(
    "/recommendations/{recommendation_id}/feedback",
    response_model=RecommendationRead,
)
async def update_recommendation_feedback(
    recommendation_id: uuid.UUID,
    payload: RecommendationFeedbackUpdate,
    current_user: CurrentUser,
    service: Service,
) -> Recommendation:
    """Mark one recommendation won't-follow or not helpful, or undo the mark (F8.9).

    A marked recommendation stays on its goal and steers later advice away from it;
    one that is not the user's is a 404 (N2).
    """
    return await service.update_feedback(recommendation_id, payload.feedback)
