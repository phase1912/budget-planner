"""Runs the section 8 NFR Gherkin scenarios (F0.10.1).

Skipped until the epic owning each NFR exists to implement it against — N1/N3/N5
land with E10 (Security, Privacy & Observability), N2 partly with E1 (Identity &
Account, F1.3's data scoping) and partly E10, N4 with E3 (Receipt Parsing &
Extraction). Delete this module-level skip, and add step definitions per
scenario as its owning epic lands — a scenario does not need every other one's
epic finished first.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.skip(reason="Awaiting E1/E3/E10 — see module docstring for which NFR")

scenarios("cross_cutting.feature")
