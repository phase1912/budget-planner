"""Runs BR-2's Gherkin scenarios (F0.6.2).

Skipped until E4 (Multi-Photo Position Matching) exists to implement the
Given/When/Then steps against. Delete this module-level skip, and add step
definitions bound to the real position-matching logic, as part of that epic.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.skip(reason="Awaiting E4 multi-photo position matching implementation")

scenarios("multi_photo_position_matching.feature")
