import logging
import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import AdviceUnavailableError, InsufficientDataError, NotFoundError
from app.domain.advice import AdviceReadiness, assess_readiness, keep_specific, project_impact
from app.domain.categories import ItemView
from app.domain.goal_pace import PACED_KINDS, GoalPace, pace
from app.domain.goals import FinancialKind
from app.domain.periods import DateRange
from app.models.goal import Goal
from app.models.recommendation import Recommendation
from app.ports.advice_generation import AdviceGeneratorPort, AdviceUnavailable
from app.repository.category import CategoryRepository
from app.repository.goal import GoalRepository
from app.repository.receipt import ReceiptRepository
from app.repository.recommendation import RecommendationRepository
from app.services.goal_analysis import GoalAnalysisService
from app.services.statistics import StatisticsService

logger = logging.getLogger(__name__)


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

    async def pace(self, goal: Goal, as_of: date) -> GoalPace | None:
        """Where a monthly money goal's month is heading, or None for any other goal (F6).

        Counts this month's spend up to `as_of` the way the month view does: parsed
        receipts only (D1, D3), on everything for a ceiling and on the one category
        for a category reduction.
        """
        if goal.financial_kind not in PACED_KINDS or goal.target_amount is None:
            return None
        month = DateRange(as_of.replace(day=1), as_of)
        if goal.financial_kind is FinancialKind.CATEGORY_REDUCTION:
            spent = (
                await self.receipts.item_spend(
                    ItemView.ALL, period=month, category_id=goal.category_id
                )
            ).total
        else:
            spent, _ = await self.receipts.month_total(month)
        return pace(spent, goal.target_amount, as_of)

    async def progress(self, as_of: date) -> list[tuple[Goal, GoalPace]]:
        """Every monthly money goal of the user's with its pace this month (F6)."""
        paced = []
        for goal in await self.goals.list_mine():
            goal_pace = await self.pace(goal, as_of)
            if goal_pace is not None:
                paced.append((goal, goal_pace))
        return paced

    async def dismiss_warning(self, goal_id: uuid.UUID, as_of: date) -> None:
        """Set a goal's at-risk warning aside until the month `as_of` falls in ends (F7).

        Raises NotFoundError for a goal that is not the user's (N2).
        """
        goal = await self.goals.get(goal_id)
        if goal is None:
            raise NotFoundError("Goal not found")
        goal.warning_dismissed_for = as_of.replace(day=1)
        await self.goals.session.flush()

    async def prepare_for_goals_at_risk(self, as_of: date, currency: str) -> int:
        """Have cut advice waiting on every goal heading over its cap (BRD F7 — F8.8).

        Runs unasked, in the background. A goal at risk that has no advice from
        this month gets some, so the warning arrives with a way to correct course;
        advice the user already has this month, asked for or not, is left alone,
        which also keeps the model to one call per goal per month. Returns how
        many goals were given advice.
        """
        month_start = as_of.replace(day=1)
        prepared = 0
        for goal, goal_pace in await self.progress(as_of):
            if not goal_pace.at_risk:
                continue
            if await self.recommendations.has_advice_since(goal.id, month_start):
                continue
            try:
                fresh = await self.advise(goal.id, as_of=as_of, currency=currency)
            except InsufficientDataError:
                return prepared  # the user's history, not this goal: no other goal will do better
            except AdviceUnavailableError:
                logger.warning("No advice could be prepared for goal %s", goal.id)
                continue
            prepared += 1 if fresh else 0
        return prepared

    async def advise(
        self, goal_id: uuid.UUID, *, as_of: date, currency: str
    ) -> Sequence[Recommendation]:
        """Replace a goal's advice with fresh advice drawn from the history to `as_of`.

        Only proposals naming a category or purchase the analysis found are kept
        (`keep_specific`, constraint 11.3); none may survive, and then the goal
        has no advice rather than generic advice. What each is worth comes from
        the same history, never from the model (`project_impact`, F4).

        A monthly money goal heading under its cap gets no advice at all, and loses
        what it had: there is nothing to cut (F6), and the card says so from `pace`.

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
        goal_pace = await self.pace(goal, as_of)
        if goal_pace is not None and goal_pace.on_track:
            # Nothing to cut (F6): earlier cut advice would now be wrong, so it goes too.
            await self.recommendations.replace_for_goal(goal.id, [])
            return []
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


def build_advice_service(
    session: AsyncSession,
    generator: AdviceGeneratorPort,
    *,
    required_receipts: int,
    required_days: int,
) -> AdviceService:
    """An AdviceService on `session`, for a request or for the background job alike."""
    receipts = ReceiptRepository(session)
    analysis = GoalAnalysisService(
        StatisticsService(receipts), receipts, CategoryRepository(session)
    )
    return AdviceService(
        GoalRepository(session),
        analysis,
        generator,
        RecommendationRepository(session),
        receipts,
        required_receipts=required_receipts,
        required_days=required_days,
    )
