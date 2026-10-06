from datetime import date

from app.domain.goal_analysis import (
    RECURRING_ITEMS_MAX,
    RECURRING_MIN_RECEIPTS,
    TOP_CATEGORIES,
    TOP_INCREASES,
    DismissedRecommendation,
    GoalAnalysis,
    GoalBrief,
    GoalScope,
    RecurringItem,
    analysis_window,
    largest_increases,
    scope_of,
)
from app.domain.periods import DateRange
from app.models.goal import Goal
from app.repository.category import CategoryRepository
from app.repository.receipt import ReceiptRepository
from app.services.statistics import StatisticsService


class GoalAnalysisService:
    """Collects the evidence advice on a goal must cite (BRD F2 — F8.3.1).

    Reads the current user's receipts only; the figures come from the same
    statistics the Statistics screen shows, so advice and screen never disagree.
    """

    def __init__(
        self,
        statistics: StatisticsService,
        receipts: ReceiptRepository,
        categories: CategoryRepository,
    ) -> None:
        self.statistics = statistics
        self.receipts = receipts
        self.categories = categories

    async def analyse(
        self, goal: Goal, as_of: date, dismissed: list[DismissedRecommendation] | None = None
    ) -> GoalAnalysis:
        """What stands out in the spending `goal` concerns, over the history to `as_of`.

        The highest-spend categories and the largest increases cover all spending,
        since either may be the lever; the goal's own categories and the recurring
        purchases are narrowed to what it concerns (`scope_of`). `goal` must be
        the current user's, the one whose receipts are read.
        """
        brief = await self._brief(goal)
        scope = scope_of(brief)
        window = analysis_window(as_of)
        stats = await self.statistics.category_statistics(window, compare=True)
        comparison = stats.comparison
        assert comparison is not None  # asked for with compare=True

        return GoalAnalysis(
            goal=brief,
            scope=scope,
            window=window,
            compared_with=comparison.period,
            receipt_count=stats.receipt_count,
            highest_spend=stats.categories[:TOP_CATEGORIES],
            largest_increases=largest_increases(comparison.changes, TOP_INCREASES),
            goal_categories=[c for c in stats.categories if c.category_id in scope.category_ids],
            recurring_items=await self._recurring(scope, window),
            dismissed_recommendations=dismissed or [],
        )

    async def _brief(self, goal: Goal) -> GoalBrief:
        category = (
            await self.categories.get_available(goal.category_id, goal.user_id)
            if goal.category_id
            else None
        )
        return GoalBrief(
            name=goal.name,
            description=goal.description,
            type=goal.type,
            financial_kind=goal.financial_kind,
            target_amount=goal.target_amount,
            category_id=goal.category_id,
            category_name=category.name if category else None,
            mapped_category_ids=tuple(goal.mapped_category_ids),
            mapped_item_names=tuple(goal.mapped_item_names),
        )

    async def _recurring(self, scope: GoalScope, window: DateRange) -> list[RecurringItem]:
        if scope.is_empty:
            return []
        purchases = await self.receipts.recurring_purchases(
            window,
            category_ids=scope.category_ids,
            keywords=scope.keywords,
            min_receipts=RECURRING_MIN_RECEIPTS,
            limit=RECURRING_ITEMS_MAX,
        )
        reach = await self.receipts.purchase_merchants(window, [p.key for p in purchases])
        shop_totals = await self.receipts.receipts_by_merchant(window)
        # Each product's shop is the one whose receipts carry it most often.
        best: dict[str, tuple[str, int]] = {}
        for key, merchant, count in sorted(reach, key=lambda r: (-r[2], r[1])):
            best.setdefault(key, (merchant, count))

        items = []
        for p in purchases:
            merchant, carried = best.get(p.key, ("", 0))
            items.append(
                RecurringItem(
                    name=p.name,
                    receipt_count=p.receipt_count,
                    total=p.total,
                    merchant=merchant or None,
                    merchant_receipts=carried,
                    merchant_receipt_total=shop_totals.get(merchant, 0),
                )
            )
        return items
