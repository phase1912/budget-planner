"""Goals in words — set, changed, dropped, and listed (F21.5, F21.7). Saving goes through
the goal service, so a lifestyle goal is mapped to what it watches as on the Goals screen."""

import json
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

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
from app.domain.goals import FinancialKind, GoalType
from app.models.goal import Goal
from app.repository.category import CategoryRepository
from app.repository.goal import GoalRepository
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.goal import GoalService

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
        "amount aside; category_reduction: one category under amount a month; lifestyle: a "
        "way of living, no amount"
    )
    amount: Amount | None = None
    category: str | None = Field(None, description="For category_reduction: the category")


class GoalCard(BaseModel):
    """A goal as the user approves it: the category by its id."""

    name: str = Field(min_length=1, max_length=120)
    kind: GoalKind
    amount: Amount | None = None
    category_id: uuid.UUID | None = None


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
    )

    async def propose(self, ctx: ToolContext, args: GoalArgs) -> dict[str, Any]:
        return {
            "name": args.name,
            "kind": args.kind,
            "amount": str(args.amount) if args.amount is not None else None,
            "category_id": await _category_id(ctx, args.category),
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


class Goals(Reader):
    """The user's goals: what each is and its amount."""

    name = "goals"
    description = "The user's goals: names, kinds and amounts."
    args = NoArgs

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        goals = await GoalRepository(ctx.session).list_mine()
        return Answer(
            json.dumps(
                {
                    "currency": ctx.user.currency,
                    "goals": [
                        {
                            "name": g.name,
                            "kind": g.financial_kind.value if g.financial_kind else "lifestyle",
                            "amount": str(g.target_amount) if g.target_amount else None,
                        }
                        for g in goals
                    ],
                }
            )
        )
