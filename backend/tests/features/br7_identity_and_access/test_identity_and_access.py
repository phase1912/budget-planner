"""Runs BR-7's Gherkin scenarios (F0.10.1).

Skipped until E1 (Identity & Account) exists to implement the Given/When/Then
steps against — there is no registration, login or OIDC flow to drive yet.
Delete this module-level skip, and add step definitions bound to the real
auth flows, as part of that epic.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.skip(reason="Awaiting E1 identity and account implementation")

scenarios("identity_and_access.feature")
