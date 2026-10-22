"""The family's spending in words (F21.13): who spent how much, and on what (F12.5, F12.9).

Read through the same household service the family view uses, so a member's private
receipts count only as one sum of theirs and never say what was bought (ADR-0017, 11h).
"""

import json

from pydantic import Field

from app.api.errors import NotFoundError
from app.assistant.tools.base import Answer, Reader, ToolContext
from app.assistant.tools.spending import MonthArgs
from app.domain.periods import DateRange
from app.repository.household import HouseholdRepository
from app.repository.household_spend import HouseholdSpendRepository
from app.services.household import HouseholdService
from app.services.household_budget import HouseholdBudgetService

TOP_CATEGORIES = 8


class FamilyArgs(MonthArgs):
    """Which month, and optionally one member."""

    member: str | None = Field(None, description="A family member's first name, or none for all")


class FamilySpending(Reader):
    """The family's month: each member's spending, shared and private, and the shared
    categories with who bought what in each."""

    name = "family_spending"
    description = (
        "How the family spends in a month: each member's total (shared and private), the "
        "family budget, and the shared categories with each member's part. For questions "
        "about a partner's, child's or the whole family's spending."
    )
    args = FamilyArgs

    async def read(self, ctx: ToolContext, args: FamilyArgs) -> Answer:
        service = HouseholdBudgetService(
            HouseholdService(HouseholdRepository(ctx.session)),
            HouseholdSpendRepository(ctx.session),
        )
        month = args.budget_month(ctx.today)
        try:
            summary = await service.month(ctx.user, month, ctx.today)
            stats = await service.statistics(ctx.user, DateRange.of_month(month))
        except NotFoundError:
            return Answer(json.dumps({"error": "the user is in no family"}))
        names = {m.user_id: m.first_name for m in summary.members}
        wanted = (args.member or "").strip().lower()
        members = [m for m in summary.members if not wanted or m.first_name.lower() == wanted]
        days = DateRange.of_month(month)
        figures = {
            "month": f"{month.year}-{month.month:02d}",
            "currency": ctx.user.currency,
            "total": str(summary.total),
            "family_budget": str(summary.limit.limit) if summary.limit else None,
            "members": [
                {
                    "name": m.first_name,
                    "total": str(m.total),
                    "shared": str(m.shared_total),
                    "private": str(m.private_total),
                }
                for m in members
            ],
            "shared_categories": [
                {
                    "category": c.spend.name,
                    "total": str(c.spend.total),
                    "by_member": {
                        names.get(uid, "?"): str(amount)
                        for uid, amount in c.members.items()
                        if not wanted or names.get(uid, "").lower() == wanted
                    },
                }
                for c in stats.categories[:TOP_CATEGORIES]
            ],
            "private_receipts_say_only_their_sum": True,
        }
        return Answer(
            json.dumps(figures, ensure_ascii=False),
            {"screen": "spending", "to": f"/spending?start={days.start}&end={days.end}"},
        )
