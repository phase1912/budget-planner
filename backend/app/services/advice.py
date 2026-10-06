import uuid
from collections.abc import Sequence
from datetime import date

from app.api.errors import AdviceUnavailableError, InsufficientDataError, NotFoundError
from app.domain.advice import AdviceReadiness, assess_readiness, keep_specific, project_impact
from app.models.recommendation import Recommendation
from app.ports.advice_generation import AdviceGeneratorPort, AdviceUnavailable
from app.repository.goal import GoalRepository
from app.repository.receipt import ReceiptRepository
from app.repository.recommendation import RecommendationRepository
from app.services.goal_analysis import GoalAnalysisService


class AdviceService:
    """Advice on the user's goals, built from their own receipts (BRD F2, F3 — F8.4)."""

    def __init__(
        self,
        goals: GoalRepository,
        analysis: GoalAnalysisService,
        generator: AdviceGeneratorPort,
        recommendations: RecommendationRepository,
        receipts: ReceiptRepository,
        *,
        required_receipts: int,
        required_days: int,
    ) -> None:
        self.goals = goals
        self.analysis = analysis
        self.generator = generator
        self.recommendations = recommendations
        self.receipts = receipts
        self.required_receipts = required_receipts
        self.required_days = required_days

    async def readiness(self, as_of: date) -> AdviceReadiness:
        """Whether the user has enough history for advice yet, and how close they are (F5)."""
        receipts, first_purchase = await self.receipts.history_extent()
        return assess_readiness(
            receipts,
            first_purchase,
            as_of,
            required_receipts=self.required_receipts,
            required_days=self.required_days,
        )

    async def list_mine(self) -> Sequence[Recommendation]:
        """Every current recommendation on the user's goals, newest first."""
        return await self.recommendations.list_mine()

    async def advise(
        self, goal_id: uuid.UUID, *, as_of: date, currency: str
    ) -> Sequence[Recommendation]:
        """Replace a goal's advice with fresh advice drawn from the history to `as_of`.

        Only proposals naming a category or purchase the analysis found are kept
        (`keep_specific`, constraint 11.3); none may survive, and then the goal
        has no advice rather than generic advice. What each is worth comes from
        the same history, never from the model (`project_impact`, F4).

        Raises NotFoundError for a goal that is not the user's (N2);
        InsufficientDataError, before any model is asked, when there is not yet
        enough history (F5); and AdviceUnavailableError, leaving the earlier advice
        in place, when the model gives no answer.
        """
        goal = await self.goals.get(goal_id)
        if goal is None:
            raise NotFoundError("Goal not found")
        readiness = await self.readiness(as_of)
        if not readiness.ready:
            raise InsufficientDataError(_not_enough(readiness))
        analysis = await self.analysis.analyse(goal, as_of)
        try:
            proposed = await self.generator.propose(analysis, currency)
        except AdviceUnavailable as error:
            raise AdviceUnavailableError(
                "Advice could not be worked out just now. Try again in a moment."
            ) from error
        fresh = []
        for advice in keep_specific(proposed, analysis):
            impact = project_impact(advice, analysis)
            fresh.append(
                Recommendation(
                    user_id=goal.user_id,
                    goal_id=goal.id,
                    target_kind=advice.target_kind,
                    target_name=advice.target_name,
                    action=advice.action,
                    rationale=advice.rationale,
                    reduction_percent=advice.reduction_percent,
                    monthly_saving=impact.monthly_saving,
                    purchases_avoided=impact.purchases_avoided,
                )
            )
        await self.recommendations.replace_for_goal(goal.id, fresh)
        return fresh


def _not_enough(readiness: AdviceReadiness) -> str:
    receipts = "receipt" if readiness.receipts == 1 else "receipts"
    days = "day" if readiness.history_days == 1 else "days"
    return (
        f"Advice needs about a month of shopping and at least {readiness.required_receipts} "
        f"receipts behind it; you have {readiness.receipts} {receipts} over "
        f"{readiness.history_days} {days}. Keep uploading and it turns on by itself."
    )
