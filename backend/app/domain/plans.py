"""What each plan gives, and which plan an account is on (F18.2, F18.4)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Plan(StrEnum):
    """The plans an account can be on. Payments come later (F18.3); grants come first."""

    FREE = "free"
    PAID = "paid"


@dataclass(frozen=True)
class PlanTerms:
    """What a plan gives: AI credits a month (F21.9), and whether ads may show (E19)."""

    monthly_credits: int
    ad_free: bool


def plan_terms(plan: Plan, free_credits: int, paid_credits: int) -> PlanTerms:
    """The terms of `plan`, with the limits the deployment configures (F18.2.2, F21.9)."""
    if plan is Plan.PAID:
        return PlanTerms(monthly_credits=paid_credits, ad_free=True)
    return PlanTerms(monthly_credits=free_credits, ad_free=False)


@dataclass(frozen=True)
class GrantedPeriod:
    """A plan an admin granted, as far as deciding the current plan needs."""

    plan: Plan
    starts_at: datetime
    ends_at: datetime
    revoked: bool


def current_plan(grants: Sequence[GrantedPeriod], now: datetime) -> tuple[Plan, datetime | None]:
    """The plan in force now and when it ends; free, with no end, when no grant runs.

    A revoked grant, or one not started or already over, gives nothing. The end runs on
    through grants that begin by the time the one before ends, so a plan extended by a
    later grant shows its real last day, and extending never shortens it.
    """
    paid = [g for g in grants if not g.revoked and g.plan != Plan.FREE]
    running = [g for g in paid if g.starts_at <= now < g.ends_at]
    if not running:
        return Plan.FREE, None
    plan = max(running, key=lambda g: g.ends_at).plan
    ends = max(g.ends_at for g in running)
    for g in sorted(paid, key=lambda g: g.starts_at):
        if g.starts_at <= ends < g.ends_at:
            ends = g.ends_at
    return plan, ends
