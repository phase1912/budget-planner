"""Runs BR-1's Gherkin scenarios (F0.6.2).

Skipped until E2 (Receipt Ingestion & Storage) and E3 (Receipt Parsing &
Extraction) exist to implement the Given/When/Then steps against — there is no
upload endpoint or parser to drive yet. Delete this module-level skip, and add
step definitions bound to the real ingestion pipeline, as part of the task in
that epic that first makes a step here true.
"""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.skip(reason="Awaiting E2/E3 receipt ingestion and parsing implementation")

scenarios("receipt_digitization.feature")
