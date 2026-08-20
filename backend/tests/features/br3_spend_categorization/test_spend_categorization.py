"""Runs BR-3's Gherkin scenarios (F0.6.2).

Skipped until E5 (Spend Categorization) exists to implement the Given/When/Then
steps against. Delete this module-level skip, and add step definitions bound to
the real categoriser, as part of that epic.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.skip(reason="Awaiting E5 spend categorization implementation")

scenarios("spend_categorization.feature")
