"""Runs BR-5's Gherkin scenarios (F0.6.2).

Skipped until E7 (Statistics, Comparison & Export) exists to implement the
Given/When/Then steps against. Delete this module-level skip, and add step
definitions bound to the real statistics engine, as part of that epic.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.skip(reason="Awaiting E7 statistics and comparison implementation")

scenarios("category_statistics.feature")
