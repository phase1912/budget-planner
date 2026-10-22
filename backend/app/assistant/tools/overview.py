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
        "waits for review, AI credits left as receipts and messages. For 'what do you know "
        "about me' or a wide question."
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
            "ai_credits_left": {
                "about_receipts": quota.receipts_left,
                "about_messages": quota.messages_left,
                "renews_on": str(quota.resets_on),
                "plan": quota.plan,
            },
        }
        return Answer(json.dumps(figures, default=str), {"screen": "home", "to": "/"})


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _when(day: int | None, weekday: int | None) -> str:
    if weekday is not None:
        return f"every {WEEKDAYS[weekday]}"
    return f"on day {day}" if day else "monthly"


async def known(ctx: ToolContext) -> str:
    """What the user has, in a few lines for the model to resolve what they mean (F21.13.2).

    Cards in the order the Accounts screen lists them, numbered, with the one that pays
    for purchases marked; the budget, regular bills and incomes, goals, saved product
    groups, recent trips and the family. Names only and the figures a reference needs —
    the read tools hold the rest. Only the caller's own things, and what their family
    shares with them (N2).
    """
    from app.repository.goal import GoalRepository
    from app.repository.product import ProductRepository
    from app.services.income import IncomeService
    from app.services.money_accounts import AccountService

    user, currency = ctx.user, ctx.user.currency
    lines: list[str] = []
    cards = (await AccountService(ctx.session).overview(ctx.today)).accounts
    if cards:
        lines.append("Cards and accounts (as numbered on the Accounts screen):")
        for n, view in enumerate(cards, 1):
            a = view.account
            role = ", pays for purchases" if a.for_purchases else ""
            kind = {"deposit": "savings", "business": "business account"}.get(str(a.kind), "card")
            lines.append(f"  {n}. {a.name} — {kind}{role}, {view.ledger.balance} {currency}")
    else:
        lines.append("No cards: the user keeps a budget only.")
    lines.append(
        f"Monthly budget: {user.budget_limit} {currency}"
        if user.budget_limit
        else "No monthly budget set."
    )
    incomes = IncomeService(ctx.session)
    bills = await incomes.regular_bills()
    if bills:
        lines.append(
            "Regular bills: "
            + "; ".join(f"{b.name} {b.amount} {_when(b.day, b.weekday)}" for b in bills)
        )
    sources = await incomes.regular_incomes()
    if sources:
        lines.append(
            "Regular incomes: "
            + "; ".join(f"{s.name} {s.amount} {_when(s.day, s.weekday)}" for s in sources)
        )
    goals = await GoalRepository(ctx.session).list_mine()
    if goals:
        lines.append(
            "Goals: "
            + "; ".join(
                f"{g.name} ({g.financial_kind.value if g.financial_kind else 'lifestyle'}"
                + (f", {g.target_amount}" if g.target_amount else "")
                + ")"
                for g in goals
            )
        )
    groups = await ProductRepository(ctx.session).selections(user.id)
    if groups:
        lines.append("Saved product groups: " + "; ".join(g.name for g in groups))
    trips = sorted(
        await TripService(ctx.session).list_trips(user.id),
        key=lambda t: t.trip.start_date,
        reverse=True,
    )[:TRIPS_LISTED]
    if trips:
        lines.append(
            "Trips: "
            + "; ".join(f"{t.trip.name} {t.trip.start_date} to {t.trip.end_date}" for t in trips)
        )
    membership = await HouseholdRepository(ctx.session).membership_of(user.id)
    if membership:
        people = [
            f"{m.user.first_name} ({m.role}{', the user' if m.user_id == user.id else ''})"
            for m in membership.household.members
        ]
        lines.append(f"Family '{membership.household.name}': " + ", ".join(people))
    return "\n".join(lines)
