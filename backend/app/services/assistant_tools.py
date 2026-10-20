"""What the assistant may do, each a narrow function over a service the screens use
(F21.1, F21.7, ADR-0025).

A read tool answers at once. A write tool only turns its arguments into a card; the card
is written when the user approves it, through the same service the screen calls, so
ownership (N2), quotas and every rule hold as they do on the screens. Settings, the
account and deleting have no tool.
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.api.errors import DomainError, ProblemCode
from app.domain.budget import BudgetMonth
from app.domain.categories import ItemView
from app.domain.income import IncomeKind
from app.domain.periods import DateRange
from app.models.user import User
from app.ports.assistant import ToolCall, ToolSpec
from app.repository.receipt import ReceiptRepository
from app.repository.snapshot import MonthlySnapshotRepository
from app.schemas.income import IncomeRequest, RegularExpenseRequest
from app.schemas.user import UserUpdateRequest
from app.services.budget import BudgetService
from app.services.income import IncomeService
from app.services.user import UserService


class MonthArgs(BaseModel):
    """Which month: YYYY-MM; this month when left out."""

    month: str | None = Field(None, pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")


class BudgetArgs(BaseModel):
    """The monthly spending budget to set."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, description="Per month")


class IncomeArgs(BaseModel):
    """Money that came in, as the Plan's "Add income" takes it."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    source: str = Field(min_length=1, max_length=80, description="Who paid, e.g. an employer")
    received_on: date | None = Field(None, description="YYYY-MM-DD; today when left out")
    kind: IncomeKind = IncomeKind.SALARY
    shared: bool = Field(False, description="Shared with the family")


class BillArgs(BaseModel):
    """A bill that goes every month by itself, as the Plan's regular bills take it."""

    name: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, description="Per month")
    day: int | None = Field(None, ge=1, le=31, description="Day of the month; 31 is the last")
    shared: bool = Field(False, description="Shared with the family")


@dataclass(frozen=True)
class Card:
    """A proposed write: what kind of thing, and its fields as the user may change them."""

    kind: str
    fields: dict[str, Any]


READS: dict[str, tuple[str, type[BaseModel]]] = {
    "month_summary": (
        "What the user spent in a month, against their budget, and their income.",
        MonthArgs,
    ),
    "spending_by_category": ("What the user spent in a month, by category.", MonthArgs),
}
WRITES: dict[str, tuple[str, type[BaseModel]]] = {
    "set_monthly_budget": ("Propose the user's monthly spending budget.", BudgetArgs),
    "add_income": ("Propose recording money that came in.", IncomeArgs),
    "add_bill": ("Propose a bill that goes every month by itself.", BillArgs),
}
CARD_KIND = {"set_monthly_budget": "budget", "add_income": "income", "add_bill": "bill"}
ARGS_OF_CARD: dict[str, type[BaseModel]] = {
    "budget": BudgetArgs,
    "income": IncomeArgs,
    "bill": BillArgs,
}


def tool_specs() -> list[ToolSpec]:
    """Every tool the assistant is offered, with its arguments' schema."""
    return [
        ToolSpec(name, description, args.model_json_schema(), writes)
        for writes, table in ((False, READS), (True, WRITES))
        for name, (description, args) in table.items()
    ]


def _month(args: MonthArgs, today: date) -> BudgetMonth:
    if args.month:
        year, month = (int(part) for part in args.month.split("-"))
        return BudgetMonth(year, month)
    return BudgetMonth(today.year, today.month)


class Toolbox:
    """The tools, bound to the signed-in user and their session for one request."""

    def __init__(self, session: Any, user: User, today: date) -> None:
        self.session = session
        self.user = user
        self.today = today

    async def read(self, call: ToolCall) -> str:
        """Run a read tool; a call the model got wrong is answered as such, not raised."""
        if call.name not in READS:
            return json.dumps({"error": f"no read tool {call.name}"})
        try:
            args = MonthArgs.model_validate(call.args)
        except ValidationError as exc:
            return json.dumps({"error": str(exc)})
        month = _month(args, self.today)
        if call.name == "month_summary":
            return await self._month_summary(month)
        return await self._by_category(month)

    def propose(self, call: ToolCall) -> Card | None:
        """The card a write tool proposes, or None for a call that cannot become one."""
        if call.name not in WRITES:
            return None
        _, model = WRITES[call.name]
        try:
            args = model.model_validate(call.args)
        except ValidationError:
            return None
        fields = args.model_dump(mode="json")
        if isinstance(args, IncomeArgs) and args.received_on is None:
            fields["received_on"] = self.today.isoformat()
        return Card(CARD_KIND[call.name], fields)

    async def save(self, card: Card) -> str:
        """Write an approved card through its service; returns what it created.

        Raises DomainError (invalid_card) for fields that do not hold, and whatever the
        service raises — the same refusals the screen would show.
        """
        model = ARGS_OF_CARD.get(card.kind)
        if model is None:
            raise DomainError("This card cannot be saved.", code=ProblemCode.INVALID_CARD)
        try:
            args = model.model_validate(card.fields)
        except ValidationError as exc:
            raise DomainError("Check the card's fields.", code=ProblemCode.INVALID_CARD) from exc
        if isinstance(args, BudgetArgs):
            await UserService(self.session).update_profile(
                self.user, UserUpdateRequest(budget_limit=args.amount)
            )
            return "plan:budget"
        income = IncomeService(self.session)
        if isinstance(args, IncomeArgs):
            entry = await income.add(
                IncomeRequest(
                    received_on=args.received_on or self.today,
                    amount=args.amount,
                    source=args.source,
                    kind=args.kind,
                    shared=args.shared,
                )
            )
            return f"income:{entry.id}"
        assert isinstance(args, BillArgs)
        bill = await income.add_bill(
            RegularExpenseRequest(
                name=args.name, amount=args.amount, day=args.day, shared=args.shared
            ),
            self.today,
        )
        return f"bill:{bill.id}"

    async def _month_summary(self, month: BudgetMonth) -> str:
        summary = await BudgetService(
            ReceiptRepository(self.session), MonthlySnapshotRepository(self.session)
        ).month_summary(
            month,
            self.today,
            user_id=self.user.id,
            now=datetime.now(UTC),
            limit=self.user.budget_limit,
        )
        income = await IncomeService(self.session).month(
            self.user, date(month.year, month.month, 1)
        )
        return json.dumps(
            {
                "month": f"{month.year}-{month.month:02d}",
                "spent": str(summary.total),
                "receipts": summary.receipt_count,
                "budget": str(summary.limit.limit) if summary.limit else None,
                "left_of_budget": str(summary.limit.remaining) if summary.limit else None,
                "income": str(income.income.net) if income.income.net is not None else None,
                "currency": self.user.currency,
            }
        )

    async def _by_category(self, month: BudgetMonth) -> str:
        rows = await ReceiptRepository(self.session).spend_by_category(
            ItemView.ALL, period=DateRange.of_month(month)
        )
        return json.dumps(
            {
                "month": f"{month.year}-{month.month:02d}",
                "currency": self.user.currency,
                "categories": [
                    {"name": r.name or "Uncategorized", "spent": str(r.total)} for r in rows[:10]
                ],
            }
        )
