"""Goals in words — set, changed, dropped, and listed (F21.5, F21.7). Saving goes through
the goal service, so a lifestyle goal is mapped to what it watches as on the Goals screen."""

import json
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.api.errors import AdviceUnavailableError, InsufficientDataError
from app.assistant.tools.base import (
    Amount,
    Answer,
    FormField,
    Reader,
    ToolContext,
    Writer,
    as_id,
    find_by_name,
)
from app.core.config import get_settings
from app.domain.goals import FinancialKind, GoalType
from app.domain.periods import DateRange
from app.models.goal import Goal
from app.ports.advice_generation import AdviceUnavailable
from app.repository.category import CategoryRepository
from app.repository.goal import GoalRepository
from app.repository.receipt import ReceiptRepository
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.advice import build_advice_service
from app.services.goal import GoalService
from app.services.goal_progress import GoalProgressService, GoalStanding

GoalKind = Literal["spending_ceiling", "savings_target", "category_reduction", "lifestyle"]
KINDS: tuple[str, ...] = ("spending_ceiling", "savings_target", "category_reduction", "lifestyle")


def _service(ctx: ToolContext) -> GoalService:
    if ctx.goal_mapper is None:
        raise RuntimeError("Goal tools need a goal mapper")
    return GoalService(
        GoalRepository(ctx.session), CategoryRepository(ctx.session), ctx.goal_mapper
    )


class GoalArgs(BaseModel):
    """A goal as the user says it."""

    name: str = Field(min_length=1, max_length=120, description="e.g. Holiday in June")
    kind: GoalKind = Field(
        description="spending_ceiling: a month's spending under amount; savings_target: put "
        "amount aside in all; category_reduction: one category under amount a month; "
        "lifestyle: a way of living, no amount"
    )
    amount: Amount | None = None
    category: str | None = Field(None, description="For category_reduction: the category")
    by: date | None = Field(None, description="savings_target only: YYYY-MM-DD to save it by")


class GoalCard(BaseModel):
    """A goal as the user approves it: the category by its id."""

    name: str = Field(min_length=1, max_length=120)
    kind: GoalKind
    amount: Amount | None = None
    category_id: uuid.UUID | None = None
    by: date | None = None


async def _category_id(ctx: ToolContext, said: str | None) -> str | None:
    if not said:
        return None
    found = find_by_name(await ctx.categories(), said, lambda c: c.name)
    return str(found.item.id) if found.item else None


def _create(card: GoalCard) -> GoalCreate:
    lifestyle = card.kind == "lifestyle"
    return GoalCreate(
        type=GoalType.LIFESTYLE if lifestyle else GoalType.FINANCIAL,
        name=card.name,
        financial_kind=None if lifestyle else FinancialKind(card.kind),
        target_amount=None if lifestyle else card.amount,
        category_id=card.category_id if card.kind == "category_reduction" else None,
        target_date=card.by if card.kind == "savings_target" else None,
    )


class AddGoal(Writer):
    """A new goal, checked as the Goals screen checks it (BRD F1)."""

    name = "add_goal"
    description = (
        "Propose a goal: a spending ceiling, a sum to save, a category to cut, or a way of living."
    )
    args = GoalArgs
    card_kind = "goal"
    card = GoalCard
    form = (
        FormField("name", "text"),
        FormField("kind", "choice", options=KINDS),
        FormField("amount", "amount", required=False),
        FormField("category_id", "category", required=False),
        FormField("by", "date", required=False),
    )

    async def propose(self, ctx: ToolContext, args: GoalArgs) -> dict[str, Any]:
        return {
            "name": args.name,
            "kind": args.kind,
            "amount": str(args.amount) if args.amount is not None else None,
            "category_id": await _category_id(ctx, args.category),
            "by": args.by.isoformat() if args.by and args.kind == "savings_target" else None,
        }

    async def save(self, ctx: ToolContext, fields: GoalCard) -> str:
        goal = await _service(ctx).create(ctx.user.id, _create(fields))
        return f"goal:{goal.id}"


async def _find(ctx: ToolContext, said: str) -> tuple[Goal | None, str | None]:
    found = find_by_name(
        list(await GoalRepository(ctx.session).list_mine()), said, lambda g: g.name
    )
    return found.item, (f"goal: {found.error}" if found.error else None)


class ChangeGoalArgs(BaseModel):
    """Which goal, by its name, and what of it changes."""

    name: str = Field(min_length=1, description="The goal as the user calls it")
    new_name: str | None = Field(None, max_length=120)
    amount: Amount | None = None


class GoalChange(BaseModel):
    """A goal's change as the user approves it."""

    goal_id: uuid.UUID
    target: str
    name: str = Field(min_length=1, max_length=120)
    amount: Amount | None = None


class ChangeGoal(Writer):
    """A goal renamed or given a new amount; its kind stays what it was made as."""

    name = "change_goal"
    description = "Propose changing a goal's name or amount, found by its name."
    args = ChangeGoalArgs
    card_kind = "goal_change"
    card = GoalChange
    form = (
        FormField("target", "target"),
        FormField("name", "text"),
        FormField("amount", "amount", required=False),
    )

    async def check(self, ctx: ToolContext, args: ChangeGoalArgs) -> str | None:
        return (await _find(ctx, args.name))[1]

    async def propose(self, ctx: ToolContext, args: ChangeGoalArgs) -> dict[str, Any]:
        goal, _ = await _find(ctx, args.name)
        assert goal is not None
        amount = args.amount if args.amount is not None else goal.target_amount
        return {
            "goal_id": str(goal.id),
            "target": goal.name,
            "name": args.new_name or goal.name,
            "amount": str(amount) if amount is not None else None,
        }

    async def save(self, ctx: ToolContext, fields: GoalChange) -> str:
        change = (
            GoalUpdate(name=fields.name, target_amount=fields.amount)
            if fields.amount is not None
            else GoalUpdate(name=fields.name)
        )
        goal = await _service(ctx).update(ctx.user.id, as_id(fields.goal_id), change)
        return f"goal:{goal.id}"


class DropGoalArgs(BaseModel):
    """Which goal to drop, by its name."""

    name: str = Field(min_length=1, description="The goal as the user calls it")


class GoalDrop(BaseModel):
    """The goal to drop, as the user approves it."""

    goal_id: uuid.UUID
    target: str


class RemoveGoal(Writer):
    """A goal dropped, as from the Goals screen."""

    name = "remove_goal"
    description = "Propose removing a goal, found by its name."
    args = DropGoalArgs
    card_kind = "goal_remove"
    card = GoalDrop
    form = (FormField("target", "target"),)

    async def check(self, ctx: ToolContext, args: DropGoalArgs) -> str | None:
        return (await _find(ctx, args.name))[1]

    async def propose(self, ctx: ToolContext, args: DropGoalArgs) -> dict[str, Any]:
        goal, _ = await _find(ctx, args.name)
        assert goal is not None
        return {"goal_id": str(goal.id), "target": goal.name}

    async def save(self, ctx: ToolContext, fields: GoalDrop) -> str:
        await _service(ctx).delete(as_id(fields.goal_id))
        return f"goal:{fields.goal_id}"


class NoArgs(BaseModel):
    """Nothing to say beyond the wish itself."""


def _standing_figures(standing: GoalStanding) -> dict[str, Any]:
    """One goal and where it stands, for the model and for its answer card (F21.14)."""
    goal = standing.goal
    row: dict[str, Any] = {
        "name": goal.name,
        "kind": goal.financial_kind.value if goal.financial_kind else "lifestyle",
        "measure": standing.kind,
    }
    if standing.pace is not None:
        p = standing.pace
        row |= {
            "target": str(p.target),
            "spent_this_month": str(p.spent),
            "projected": str(p.projected),
            "on_track": p.on_track,
            "at_risk": p.at_risk,
            "percent": int(min(p.spent / p.target * 100, Decimal(100))) if p.target else 0,
        }
    if standing.savings is not None:
        sv = standing.savings
        row |= {
            "target": str(sv.target),
            "saved": str(sv.saved),
            "percent": sv.percent,
            "target_date": str(sv.target_date) if sv.target_date else None,
            "needed_per_month": str(sv.needed_per_month) if sv.needed_per_month else None,
            "reached": sv.reached,
            "overdue": sv.overdue,
        }
    if standing.lifestyle is not None:
        life = standing.lifestyle
        row |= {
            "this_month": str(life.this_month),
            "monthly_average": str(life.monthly_average),
            "change_percent": life.change_percent,
            "watches": [*goal.mapped_item_names],
        }
    return row


class Goals(Reader):
    """The user's goals and where each stands (F8.11.2, F21.5): a monthly cap's pace, a
    savings goal's money against its date, a lifestyle goal's month."""

    name = "goals"
    description = (
        "The user's goals and how each is going: a monthly cap's spending and pace, a "
        "savings goal's money saved, its date and what is needed a month, a lifestyle "
        "goal's watched spending this month against before."
    )
    args = NoArgs

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        standings = await GoalProgressService(ctx.session).standings(ctx.today)
        goals = [_standing_figures(s) for s in standings]
        figures = {"currency": ctx.user.currency, "goals": goals}
        card = {"screen": "goals", "to": "/goals", "currency": ctx.user.currency, "goals": goals}
        return Answer(json.dumps(figures, ensure_ascii=False), card if goals else None)


class GoalNameArgs(BaseModel):
    """Which goal, by its name."""

    name: str = Field(min_length=1, description="The goal as the user calls it")


class AdviceArgs(GoalNameArgs):
    """Which goal, and whether to work out fresh advice."""

    fresh: bool = Field(
        False, description="True to work out new advice from the receipts; it costs more"
    )


class GoalAdvice(Reader):
    """What to do about one goal (F8.4, F21.5): the advice it has, or fresh advice worked
    out from the receipts as the Goals screen's button does — a model call, paid from the
    AI credits."""

    name = "goal_advice"
    description = (
        "Advice on one goal from the user's own receipts: what to cut and what that saves. "
        "Gives the advice already there; fresh=true works out new advice."
    )
    args = AdviceArgs

    async def read(self, ctx: ToolContext, args: AdviceArgs) -> Answer:
        goal, error = await _find(ctx, args.name)
        if goal is None:
            return Answer(json.dumps({"error": error}))
        settings = get_settings()
        service = build_advice_service(
            ctx.session,
            ctx.advice or _NoAdvice(),
            required_receipts=settings.min_receipts_for_advice,
            required_days=settings.min_history_days_for_advice,
        )
        if args.fresh and ctx.advice is not None:
            try:
                advice = list(
                    await service.advise(
                        goal.id,
                        as_of=ctx.today,
                        currency=ctx.user.currency,
                        language=ctx.user.language or "en",
                    )
                )
            except (InsufficientDataError, AdviceUnavailableError) as exc:
                return Answer(json.dumps({"goal": goal.name, "no_advice": str(exc)}))
        else:
            advice = [r for r in await service.list_mine() if r.goal_id == goal.id]
        figures = {
            "goal": goal.name,
            "currency": ctx.user.currency,
            "advice": [
                {
                    "do": r.action,
                    "why": r.rationale,
                    "saves_a_month": str(r.monthly_saving) if r.monthly_saving else None,
                    "turned_down": r.feedback is not None,
                }
                for r in advice
            ],
        }
        return Answer(json.dumps(figures, ensure_ascii=False), {"screen": "goals", "to": "/goals"})


class _NoAdvice:
    """Stands in where no model is wired: only the advice already there can be read."""

    async def propose(self, *args: Any, **kwargs: Any) -> list[Any]:
        raise AdviceUnavailable("no advice model")


WATCHED_MONTHS = 3
LISTED_PRODUCTS = 12


class GoalProducts(Reader):
    """What the user bought that a goal concerns (F21.5): for "which products should I drop
    for my lose-weight goal?" — each line with how often and what it costs a month, as a
    table to read."""

    name = "goal_products"
    description = (
        "The purchases a goal concerns over the last three months — a lifestyle goal's "
        "watched lines, a category cut's category, a ceiling's most bought — each with how "
        "many receipts and what it costs a month."
    )
    args = GoalNameArgs

    async def read(self, ctx: ToolContext, args: GoalNameArgs) -> Answer:
        goal, error = await _find(ctx, args.name)
        if goal is None:
            return Answer(json.dumps({"error": error}))
        first = ctx.today.replace(day=1)
        index = first.year * 12 + first.month - 1 - WATCHED_MONTHS
        period = DateRange(date(index // 12, index % 12 + 1, 1), ctx.today)
        categories: tuple[uuid.UUID, ...] = ()
        keywords: tuple[str, ...] = ()
        if goal.type is GoalType.LIFESTYLE:
            categories, keywords = tuple(goal.mapped_category_ids), tuple(goal.mapped_item_names)
        elif goal.category_id is not None:
            categories = (goal.category_id,)
        bought = await ReceiptRepository(ctx.session).recurring_purchases(
            period,
            category_ids=categories,
            keywords=keywords,
            min_receipts=1,
            limit=LISTED_PRODUCTS,
        )
        months = Decimal(WATCHED_MONTHS) + Decimal(ctx.today.day) / 30
        rows = [
            {
                "name": p.name,
                "receipts": p.receipt_count,
                "a_month": str((p.total / months).quantize(Decimal("0.01"))),
                "spent": str(p.total),
            }
            for p in bought
        ]
        figures = {"goal": goal.name, "currency": ctx.user.currency, "products": rows}
        card = {
            "screen": "products",
            "to": "/goals",
            "currency": ctx.user.currency,
            "products": rows,
        }
        return Answer(json.dumps(figures, ensure_ascii=False), card if rows else None)
