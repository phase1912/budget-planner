"""A month's income, and the taxes of one who pays their own (F23.10, F23.16)."""

from datetime import date
from decimal import Decimal

from app.domain.balance import Balance
from app.domain.income import (
    IncomeKind,
    Recurring,
    TaxRule,
    month_income,
    regular_since,
    taxed_by_default,
)

RULE = TaxRule(rate=Decimal("12"), fixed=Decimal("1600"))


def test_a_month_with_entries_counts_them() -> None:
    result = month_income([(Decimal("6200"), True), (Decimal("600"), False)], usual=Decimal("6800"))
    assert result.total == Decimal("6800") and result.entered
    assert result.taxes == 0 and result.net == Decimal("6800")


def test_a_month_without_entries_shows_the_usual_income_marked_as_such() -> None:
    result = month_income([], usual=Decimal("6800"))
    assert result.total == Decimal("6800") and not result.entered


def test_no_entries_and_no_usual_income_is_unknown_not_zero() -> None:
    assert month_income([], usual=None).total is None


def test_taxes_take_a_share_of_each_taxed_income_and_the_fixed_sum_once() -> None:
    """20 000 earned and taxed, 1 000 a gift: 12 % of 20 000 plus 1 600 once."""
    result = month_income(
        [(Decimal("20000"), True), (Decimal("1000"), False)], usual=None, taxes=RULE
    )

    assert result.total == Decimal("21000")
    assert result.taxes == Decimal("4000.00")
    assert result.net == Decimal("17000.00")


def test_the_fixed_sum_is_owed_even_in_a_month_with_nothing_taxed() -> None:
    result = month_income([(Decimal("500"), False)], usual=None, taxes=RULE)
    assert result.taxes == Decimal("1600")


def test_the_usual_income_standing_in_is_taken_as_taxed() -> None:
    result = month_income([], usual=Decimal("10000"), taxes=RULE)
    assert result.taxes == Decimal("2800.00") and not result.entered


def test_earnings_are_taxed_by_default_gifts_refunds_and_sales_are_not() -> None:
    assert taxed_by_default(IncomeKind.SALARY) and taxed_by_default(IncomeKind.SIDE)
    assert not taxed_by_default(IncomeKind.OTHER) and not taxed_by_default(IncomeKind.REFUND)


def test_taxes_paid_leave_the_balance_and_what_is_still_owed() -> None:
    balance = Balance(
        since=date(2026, 10, 1),
        starting=Decimal("1000"),
        came_in=Decimal("20000"),
        spent=Decimal("3000"),
        taxes_paid=Decimal("1600"),
        taxes_owed=Decimal("4000"),
    )

    assert balance.now == Decimal("16400")
    assert balance.for_taxes == Decimal("2400")


def test_regular_incomes_count_by_themselves_and_entries_come_on_top() -> None:
    """F23.17: 10 000 and 1 000 a month, plus 500 that came unexpectedly."""
    result = month_income(
        [(Decimal("500"), False)],
        usual=Decimal("9000"),
        recurring=[(Decimal("10000"), False), (Decimal("1000"), False)],
    )

    assert result.total == Decimal("11500") and result.entered


def test_a_regular_income_runs_from_its_first_month_to_its_last() -> None:
    salary = Recurring(Decimal("10000"), 10, date(2026, 10, 18), date(2026, 12, 3))

    assert not salary.runs_in(date(2026, 9, 1))
    assert salary.runs_in(date(2026, 10, 1)) and salary.runs_in(date(2026, 12, 1))
    assert not salary.runs_in(date(2027, 1, 1))


def test_the_balance_gains_a_regular_income_on_the_day_it_arrives() -> None:
    salary = Recurring(Decimal("10000"), 10, date(2026, 9, 1), None)
    pension = Recurring(Decimal("1000"), 31, date(2026, 9, 1), None)

    assert regular_since([salary, pension], date(2026, 9, 15), date(2026, 10, 9)) == Decimal("1000")
    assert regular_since([salary, pension], date(2026, 9, 15), date(2026, 10, 10)) == Decimal(
        "11000"
    )
    # A 31st in a 30-day month arrives on the 30th.
    assert regular_since([pension], date(2026, 9, 1), date(2026, 9, 30)) == Decimal("1000")


def test_a_taxed_regular_income_is_taxed_every_month_an_untaxed_one_is_not() -> None:
    """One who pays their own taxes: 12 % of the 10 000 salary, not of the 1 000 pension."""
    result = month_income(
        [],
        usual=None,
        taxes=RULE,
        recurring=[(Decimal("10000"), True), (Decimal("1000"), False)],
    )

    assert result.taxes == Decimal("2800.00")
    assert result.net == Decimal("8200.00")


def test_a_weekly_bill_counts_as_often_as_its_weekday_falls_in_the_month() -> None:
    """F23.21: Mondays, never 4.33 of them — October 2026 has four, March 2027 five."""
    gym = Recurring(Decimal("50.00"), None, date(2026, 9, 1), None, weekday=0)

    assert gym.days_in(date(2026, 10, 1)) == [
        date(2026, 10, 5),
        date(2026, 10, 12),
        date(2026, 10, 19),
        date(2026, 10, 26),
    ]
    assert gym.in_month(date(2026, 10, 1)) == Decimal("200.00")
    assert gym.in_month(date(2027, 3, 1)) == Decimal("250.00")


def test_a_weekly_rule_started_mid_month_counts_only_from_its_first_day() -> None:
    gym = Recurring(Decimal("50.00"), None, date(2026, 10, 20), None, weekday=0)

    assert gym.days_in(date(2026, 10, 1)) == [date(2026, 10, 26)]
    assert gym.in_month(date(2026, 9, 1)) == Decimal("0")


def test_a_monthly_rule_still_comes_once_and_regular_since_counts_each_weekday() -> None:
    rent = Recurring(Decimal("1000.00"), 31, date(2026, 1, 1), None)
    gym = Recurring(Decimal("50.00"), None, date(2026, 1, 1), None, weekday=0)

    assert rent.days_in(date(2026, 2, 1)) == [date(2026, 2, 28)]
    assert rent.in_month(date(2026, 2, 1)) == Decimal("1000.00")
    assert regular_since([gym], date(2026, 10, 1), date(2026, 10, 20)) == Decimal("150.00")
