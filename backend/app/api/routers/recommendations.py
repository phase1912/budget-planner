import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.advice_generation_agent import AdviceGenerationAdapter
from app.agent.factory import agent_from_settings
from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.recommendation import Recommendation
from app.models.user import User
from app.ports.advice_generation import AdviceGeneratorPort
from app.repository.category import CategoryRepository
from app.repository.goal import GoalRepository
from app.repository.receipt import ReceiptRepository
from app.repository.recommendation import RecommendationRepository
from app.schemas.recommendation import RecommendationRead
from app.services.advice import AdviceService
from app.services.goal_analysis import GoalAnalysisService
from app.services.statistics import StatisticsService

router = APIRouter(prefix="/api/v1", tags=["advice"])


def get_advice_generator() -> AdviceGeneratorPort:
    """Provide the advice generator port; tests override this to stay off the network."""
    return AdviceGenerationAdapter(agent_from_settings())


def get_advice_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    generator: Annotated[AdviceGeneratorPort, Depends(get_advice_generator)],
) -> AdviceService:
    """The advice service bound to the request's session."""
    receipts = ReceiptRepository(session)
    analysis = GoalAnalysisService(
        StatisticsService(receipts), receipts, CategoryRepository(session)
    )
    return AdviceService(
        GoalRepository(session), analysis, generator, RecommendationRepository(session)
    )


Service = Annotated[AdviceService, Depends(get_advice_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/recommendations", response_model=list[RecommendationRead])
async def list_recommendations(
    current_user: CurrentUser, service: Service
) -> Sequence[Recommendation]:
    """Every goal's current advice for the Goals screen, in one request (BRD F3)."""
    return await service.list_mine()


@router.post(
    "/goals/{goal_id}/recommendations",
    response_model=list[RecommendationRead],
    status_code=status.HTTP_201_CREATED,
)
async def advise_on_goal(
    goal_id: uuid.UUID, current_user: CurrentUser, service: Service
) -> Sequence[Recommendation]:
    """Fresh advice on one goal, replacing its earlier advice (BRD F2, F3).

    Another user's goal is not found (N2); a model that gives no answer is 503.
    """
    return await service.advise(
        goal_id, as_of=datetime.now(UTC).date(), currency=current_user.currency
    )
