"""Checking a money goal before it is saved (F23.13)."""

import uuid
from decimal import Decimal

from app.domain.goal_check import MonthlyCategory, Unknown, Verdict, check_goal_plan
from app.domain.goals import FinancialKind

DINING = uuid.UUID(int=1)
GROCERIES = uuid.UUID(int=2)
SPEND = [
    MonthlyCategory(GROCERIES, "Groceries", Decimal("1200")),
    MonthlyCategory(DINING, "Dining", Decimal("600")),
    MonthlyCategory(None, None, Decimal("200")),
]


def _check(kind: FinancialKind, target: str, **kwargs: object):  # type: ignore[no-untyped-def]
    defaults: dict[str, object] = {
        "category_id": None,
        "months": 3,
        "monthly_spend": Decimal("2000"),
        "categories": SPEND,
        "monthly_income": Decimal("2800"),
    }
    defaults.update(kwargs)
    return check_goal_plan(kind, Decimal(target), **defaults)  # type: ignore[arg-type]


def test_a_savings_target_within_what_is_usually_left_is_doable() -> None:
    check = _check(FinancialKind.SAVINGS_TARGET, "500")

    assert check.verdict is Verdict.DOABLE
    assert check.usual == Decimal("800")
    assert check.gap == 0


def test_a_savings_target_beyond_it_is_a_stretch_with_where_the_money_could_come_from() -> None:
    check = _check(FinancialKind.SAVINGS_TARGET, "1000")

    assert check.verdict is Verdict.STRETCH
    assert check.gap == Decimal("200")
    assert [(s.name, s.cut) for s in check.sources] == [
        ("Groceries", Decimal("180")),
        ("Dining", Decimal("20")),
    ]


def test_a_savings_target_without_any_income_cannot_be_checked() -> None:
    check = _check(FinancialKind.SAVINGS_TARGET, "100", monthly_income=None)

    assert check.verdict is Verdict.UNKNOWN
    assert check.unknown is Unknown.NO_INCOME


def test_with_no_receipts_in_recent_months_there_is_nothing_to_judge() -> None:
    check = _check(FinancialKind.SPENDING_CEILING, "1000", months=0)

    assert check.verdict is Verdict.UNKNOWN
    assert check.unknown is Unknown.NO_HISTORY


def test_a_ceiling_under_the_usual_spend_is_a_stretch_by_the_difference() -> None:
    check = _check(FinancialKind.SPENDING_CEILING, "1900")

    assert check.verdict is Verdict.STRETCH
    assert check.gap == Decimal("100")
    assert check.sources[0].name == "Groceries"
    assert sum(s.cut for s in check.sources) == Decimal("100")


def test_a_category_cut_is_measured_against_that_category_alone() -> None:
    doable = _check(FinancialKind.CATEGORY_REDUCTION, "700", category_id=DINING)
    stretch = _check(FinancialKind.CATEGORY_REDUCTION, "450", category_id=DINING)

    assert doable.verdict is Verdict.DOABLE
    assert stretch.verdict is Verdict.STRETCH
    assert stretch.gap == Decimal("150")
    assert stretch.sources == []
