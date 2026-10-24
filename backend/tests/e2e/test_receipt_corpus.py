"""Every corpus case through the add-a-receipt screen (F0.11.3, F0.11.4).

A case is a folder under evaluation/corpus: its photos and a case.json saying what they
are and what the product must end with (``expect``). Adding a case adds a test here. A
case the product cannot handle yet names the feature it waits for (``waits_for``) and is
expected to fail until that lands — then it must pass, or the suite says so.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.helpers import REPO, ready_account, shot, sign_in, words

CORPUS = REPO / "backend" / "evaluation" / "corpus"


def _cases() -> list[Any]:
    cases = []
    for path in sorted(CORPUS.rglob("case.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        case_id = str(path.parent.relative_to(CORPUS))
        marks = []
        if case.get("expect", {}).get("waits_for"):
            marks.append(
                pytest.mark.xfail(strict=True, reason=f"waits for {case['expect']['waits_for']}")
            )
        cases.append(pytest.param(path.parent, case, id=case_id, marks=marks))
    return cases


def _plural(count: int) -> str:
    """Ukrainian plural form for a count, as i18next picks it."""
    if count % 10 == 1 and count % 100 != 11:
        return "one"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return "few"
    return "many"


@pytest.mark.parametrize(("folder", "case"), _cases())
def test_a_corpus_case_is_read_reviewed_and_stored(
    phone: Page, folder: Path, case: dict[str, Any]
) -> None:
    account = ready_account("corpus")
    expected = case.get("expect", {})
    receipts = int(expected.get("stored_receipts", 0))
    name = folder.name

    sign_in(phone, account, "/upload")
    files = [str(folder / file) for file in case["files"]]
    phone.locator('input[type="file"][accept*="pdf"]:not([capture])').first.set_input_files(files)
    phone.get_by_role("button", name=words("upload:add.read")).click()

    expect(phone.get_by_role("heading", name=words("upload:read.title"))).to_be_visible(
        timeout=60_000
    )
    shot(phone, name, "review")
    if receipts:
        store = words(f"upload:read.store_{_plural(receipts)}", count=str(receipts))
        phone.get_by_role("button", name=store).click()
        expect(phone.get_by_role("status")).to_be_visible()
        shot(phone, name, "stored")

    with account.api() as api:
        stored = api.get("/receipts", params={"size": 50}).json()["items"]
    documents = [d for d in case["documents"] if d.get("kind", "receipt") == "receipt"]
    assert len(stored) == receipts, f"stored {len(stored)} receipts, expected {receipts}"
    for document in documents[:receipts]:
        match = next((r for r in stored if r["merchant_name"] == document["merchant"]), None)
        assert match is not None, f"{document['merchant']} was not stored"
        assert str(match["transaction_date"]).startswith(document["date"])
        assert Decimal(str(match["original_total"] or match["total_amount"])) == Decimal(
            document["total"]
        )
    _money_moved(account, case, expected)
    if month := expected.get("stored_in_month"):
        link = phone.get_by_role("link", name=words("messages:upload.openMonth", month=""))
        expect(link.or_(phone.get_by_role("status").get_by_role("link"))).to_have_attribute(
            "href", f"/receipts?start={month}-01&end=" + _last_day(month)
        )


def _last_day(month: str) -> str:
    import calendar

    year, number = (int(part) for part in month.split("-"))
    return f"{month}-{calendar.monthrange(year, number)[1]:02d}"


def _money_moved(account: Any, case: dict[str, Any], expected: dict[str, Any]) -> None:
    """Money sent is an expense of its amount, money received an income (F21.16)."""
    sent = [d for d in case["documents"] if d.get("kind") == "money_sent"]
    received = [d for d in case["documents"] if d.get("kind") == "money_received"]
    with account.api() as api:
        if expected.get("stored_expenses"):
            stored = api.get("/receipts", params={"size": 50}).json()["items"]
            for document in sent:
                assert any(
                    Decimal(str(r["original_total"] or r["total_amount"]))
                    == Decimal(document["total"])
                    for r in stored
                ), f"no expense of {document['total']} {document['currency']}"
        if expected.get("stored_incomes"):
            for document in received:
                month = document["date"][:7]
                incomes = api.get("/api/v1/income", params={"month": month}).json()
                assert any(
                    Decimal(str(i["amount"])) == Decimal(document["total"])
                    for i in incomes.get("entries", [])
                ), f"no income of {document['total']} {document['currency']}"
