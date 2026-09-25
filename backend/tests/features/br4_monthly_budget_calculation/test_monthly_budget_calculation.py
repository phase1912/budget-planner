"""Runs BR-4's Gherkin scenarios (F0.6.2).

E6 is under way: F6.1 delivers the month total by transaction date (D1, D2),
proven in tests/api/test_budget_router.py. Every scenario below also asserts
something a later feature owns, so each stays skipped until that feature adds
its step definitions, as named in `AWAITING`.
"""

import pytest
from pytest import FixtureRequest
from pytest_bdd import scenarios

scenarios("monthly_budget_calculation.feature")

AWAITING = {
    "test_calculate_completed_months_budget": "the finalised label: F6.3 and F6.4 (D5)",
    "test_calculate_inprogress_months_budget": "the month-to-date label: F6.3 (D4)",
    "test_exclude_receipts_requiring_manual_review": "the excluded-receipts notice: F6.2 (D3)",
    "test_recalculate_budget_after_receipt_edit": "stored snapshots: F6.4 and F6.5 (D6)",
    "test_show_spend_against_a_userdefined_budget_limit": "the limit percentage: F6.6 (D7)",
}


@pytest.fixture(autouse=True)
def skip_until_its_feature_lands(request: FixtureRequest) -> None:
    reason = AWAITING.get(request.node.name)
    if reason is not None:
        pytest.skip(f"Awaiting {reason}")
