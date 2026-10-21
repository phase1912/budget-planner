"""What the app knows about the user, in one answer (F21.10.1)."""

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from app.assistant.tools.accounts import Accounts
from app.assistant.tools.base import Answer, Reader, ToolContext
from app.assistant.tools.goals import Goals
from app.assistant.tools.incomes import RegularMoney
from app.assistant.tools.spending import MonthArgs, MonthSummary
from app.core.config import get_settings
from app.repository.household import HouseholdRepository
from app.repository.receipt import ReceiptRepository
from app.services.quota import QuotaService
from app.services.trip import TripService

TRIPS_LISTED = 5


class NoArgs(BaseModel):
    """Nothing to say beyond the wish itself."""


class Overview(Reader):
    """Everything about the user the screens show, at a glance: settings, the month, cards,
    regular money, goals, the family, trips, what waits for review and the reads left. Each
    part comes from the read tool or service its screen uses, so only the caller's own data
    is read (N2)."""

    name = "overview"
    description = (
        "Everything the app knows about the user at once: settings, this month against the "
        "budget, cards and balances, regular incomes and bills, goals, family, trips, what "
        "waits for review, receipt reads left. For 'what do you know about me' or a wide "
        "question."
    )
    args = NoArgs

    async def read(self, ctx: ToolContext, args: NoArgs) -> Answer:
        user = ctx.user

        async def part(reader: Reader, reader_args: BaseModel) -> Any:
            return json.loads((await reader.read(ctx, reader_args)).figures)

        membership = await HouseholdRepository(ctx.session).membership_of(user.id)
        trips = await TripService(ctx.session).list_trips(user.id)
        quota = await QuotaService(ctx.session, get_settings()).quota_for(user, datetime.now(UTC))
        figures = {
            "settings": {
                "language": user.language,
                "currency": user.currency,
                "monthly_budget": str(user.budget_limit) if user.budget_limit else None,
                "payday": user.payday,
                "palette": user.palette,
                "travels_for_work": user.travels_for_work,
                "pays_own_taxes": user.pays_own_taxes,
            },
            "this_month": await part(MonthSummary(), MonthArgs()),
            "accounts": await part(Accounts(), NoArgs()),
            "regular": await part(RegularMoney(), NoArgs()),
            "goals": (await part(Goals(), NoArgs()))["goals"],
            "family": {
                "name": membership.household.name,
                "members": [
                    {"name": m.user.first_name, "role": m.role}
                    for m in membership.household.members
                ],
            }
            if membership
            else None,
            "trips": [
                {"name": t.trip.name, "from": str(t.trip.start_date), "to": str(t.trip.end_date)}
                for t in sorted(trips, key=lambda t: t.trip.start_date, reverse=True)[:TRIPS_LISTED]
            ],
            "lines_waiting_for_review": await ReceiptRepository(ctx.session).count_needs_review(),
            "receipt_reads": {
                "used": quota.used,
                "limit": quota.limit,
                "resets_on": str(quota.resets_on),
                "plan": quota.plan,
            },
        }
        return Answer(json.dumps(figures, default=str), {"screen": "home", "to": "/"})
