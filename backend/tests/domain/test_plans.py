"""Which plan an account is on, and what it gives (F18.2, F18.4)."""

from datetime import UTC, datetime, timedelta

from app.domain.plans import GrantedPeriod, Plan, current_plan, plan_terms

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def _grant(start_days: int, end_days: int, *, revoked: bool = False) -> GrantedPeriod:
    return GrantedPeriod(
        Plan.PAID, NOW + timedelta(days=start_days), NOW + timedelta(days=end_days), revoked
    )


def test_without_a_grant_the_account_is_on_the_free_plan() -> None:
    assert current_plan([], NOW) == (Plan.FREE, None)


def test_a_running_grant_gives_its_plan_until_it_ends() -> None:
    assert current_plan([_grant(-1, 30)], NOW) == (Plan.PAID, NOW + timedelta(days=30))


def test_a_grant_over_not_yet_started_or_revoked_gives_nothing() -> None:
    grants = [_grant(-40, -10), _grant(5, 30), _grant(-1, 30, revoked=True)]

    assert current_plan(grants, NOW) == (Plan.FREE, None)


def test_of_overlapping_grants_the_one_ending_last_decides() -> None:
    assert current_plan([_grant(-5, 10), _grant(-1, 60)], NOW)[1] == NOW + timedelta(days=60)


def test_the_paid_plan_reads_more_and_shows_no_ads() -> None:
    assert plan_terms(Plan.PAID, 10, 200).monthly_receipts == 200
    assert plan_terms(Plan.PAID, 10, 200).ad_free
    assert not plan_terms(Plan.FREE, 10, 200).ad_free


def test_a_grant_starting_when_the_running_one_ends_extends_the_plan() -> None:
    now = datetime(2026, 10, 17, tzinfo=UTC)
    first = GrantedPeriod(Plan.PAID, now - timedelta(days=1), now + timedelta(days=29), False)
    after = GrantedPeriod(Plan.PAID, first.ends_at, first.ends_at + timedelta(days=10), False)
    gap = GrantedPeriod(
        Plan.PAID, after.ends_at + timedelta(days=5), after.ends_at + timedelta(days=9), False
    )

    assert current_plan([gap, after, first], now) == (Plan.PAID, after.ends_at)
