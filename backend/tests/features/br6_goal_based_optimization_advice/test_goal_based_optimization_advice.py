"""Runs BR-6's Gherkin scenarios (F0.6.2).

Skipped until E8 (Goals & AI Optimization Advice) exists to implement the
Given/When/Then steps against. Delete this module-level skip, and add step
definitions bound to the real advice generator, as part of that epic.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.skip(reason="Awaiting E8 goals and optimization advice implementation")

scenarios("goal_based_optimization_advice.feature")
