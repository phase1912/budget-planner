"""Runs BR-4's Gherkin scenarios (F0.6.2).

Skipped until E6 (Monthly Budget Calculation) exists to implement the
Given/When/Then steps against. Delete this module-level skip, and add step
definitions bound to the real budget calculation, as part of that epic.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.skip(reason="Awaiting E6 monthly budget calculation implementation")

scenarios("monthly_budget_calculation.feature")
