"""Income lands on a card (F23.21): what the API tests send so one is there.

Most tests are about something else than where income lands. Their income requests are
sent as a user with no card would send them through the app — asking for "My card" with
the income — unless the test names an account or says `new_card` itself.
"""

import re
from typing import Any

INCOME_WRITES = re.compile(r"^/api/v1/income(/regular)?(/[0-9a-f-]{36})?$|^/api/v1/income/pending/")


def on_a_card(method: str, url: str, json: Any) -> Any:
    """`json` with a card to land on, when it is an income write that names none."""
    if (
        method in ("POST", "PUT")
        and INCOME_WRITES.match(url.split("?")[0])
        and isinstance(json, dict)
        and "account_id" not in json
        and "new_card" not in json
    ):
        return {**json, "new_card": {"name": "My card"}}
    return json
