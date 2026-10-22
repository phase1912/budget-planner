"""The monthly budget, set, changed or removed in words (F21.1, F21.7)."""

from typing import Any

from pydantic import BaseModel, Field

from app.assistant.tools.base import Amount, FormField, ToolContext, Writer
from app.schemas.user import UserUpdateRequest
from app.services.user import UserService


class BudgetArgs(BaseModel):
    """The monthly spending budget to set."""

    amount: Amount = Field(description="Per month")


class SetMonthlyBudget(Writer):
    """The budget the month is measured against (D7), as Plan sets it."""

    name = "set_monthly_budget"
    description = (
        "Propose the budget for the whole month's spending, new or changed — never a limit on "
        "one category: that is a goal (add_goal, category_reduction)."
    )
    args = BudgetArgs
    card_kind = "budget"
    card = BudgetArgs

    async def propose(self, ctx: ToolContext, args: BudgetArgs) -> dict[str, Any]:
        return args.model_dump(mode="json")

    async def save(self, ctx: ToolContext, fields: BudgetArgs) -> str:
        await UserService(ctx.session).update_profile(
            ctx.user, UserUpdateRequest(budget_limit=fields.amount)
        )
        return "plan:budget"


class NoArgs(BaseModel):
    """Nothing to say beyond the wish itself."""


class RemoveBudget(Writer):
    """No budget any more: the month is shown on its own, as when none was set (D7)."""

    name = "remove_budget"
    description = "Propose having no monthly budget any more."
    args = NoArgs
    card_kind = "budget_remove"
    card = NoArgs
    form = (FormField("budget", "target"),)

    async def check(self, ctx: ToolContext, args: NoArgs) -> str | None:
        return None if ctx.user.budget_limit is not None else "the user has no budget set"

    async def propose(self, ctx: ToolContext, args: NoArgs) -> dict[str, Any]:
        return {"budget": str(ctx.user.budget_limit)}

    async def save(self, ctx: ToolContext, fields: NoArgs) -> str:
        await UserService(ctx.session).update_profile(
            ctx.user, UserUpdateRequest(budget_limit=None)
        )
        return "plan:budget"
