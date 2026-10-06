import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.advice_generation_agent import AdviceGenerationAdapter
from app.agent.factory import agent_from_settings
from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.recommendation import Recommendation
from app.models.user import User
from app.ports.advice_generation import AdviceGeneratorPort
from app.schemas.recommendation import (
    AdviceReadinessRead,
    GoalProgressRead,
    RecommendationRead,
)
from app.services.advice import AdviceService, build_advice_service

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
    )


@router.get("/goals/progress", response_model=list[GoalProgressRead])
async def goal_progress(current_user: CurrentUser, service: Service) -> list[GoalProgressRead]:
    """Where each of the caller's monthly money goals is heading this month (BRD F6, F7).

    This is also how an at-risk warning reaches the user: worked out on every
    look, so it is never stale, and waiting for them without their asking.
    """
    today = datetime.now(UTC).date()
    return [
        GoalProgressRead(
            goal_id=goal.id,
            goal_name=goal.name,
            spent=goal_pace.spent,
            projected=goal_pace.projected,
            target=goal_pace.target,
            margin=goal_pace.margin,
            on_track=goal_pace.on_track,
            at_risk=goal_pace.at_risk,
            warning_dismissed=goal.warning_dismissed_for == today.replace(day=1),
            day=goal_pace.day,
            days_in_month=goal_pace.days_in_month,
        )
        for goal, goal_pace in await service.progress(today)
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
async def advise_on_goal(
    goal_id: uuid.UUID, current_user: CurrentUser, service: Service
) -> Sequence[Recommendation]:
    """Fresh advice on one goal, replacing its earlier advice (BRD F2, F3).

    Another user's goal is not found (N2); too little history is 422 with the code
    `insufficient_data` (F5); a model that gives no answer is 503.
    """
    return await service.advise(
        goal_id, as_of=datetime.now(UTC).date(), currency=current_user.currency
    )
