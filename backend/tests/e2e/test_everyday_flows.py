"""The flows people use every day, at phone, tablet and desktop widths (F0.11.4).

An expense with no receipt, the AI's consent refused and then given on the upload screen,
and deleting the account — each checked on screen and against the API.
"""

from decimal import Decimal

import httpx
from playwright.sync_api import Page, expect

from tests.e2e.helpers import (
    API_URL,
    REPO,
    mail_link,
    ready_account,
    register,
    shot,
    sign_in,
    words,
)

BIEDRONKA = REPO / "backend" / "evaluation" / "corpus" / "pl" / "biedronka-groceries" / "1.jpg"


def test_an_expense_with_no_receipt_is_added_and_counted(screen: Page) -> None:
    account = ready_account("expense")
    sign_in(screen, account, "/upload")
    screen.get_by_role("button", name=words("receipts:manual.openLong")).click()
    dialog = screen.get_by_role("dialog")
    dialog.get_by_label(words("receipts:manual.description")).fill("Таксі з вокзалу")
    dialog.get_by_label(words("receipts:manual.amount")).fill("45.50")
    shot(screen, "expense", "dialog")
    dialog.get_by_role("button", name=words("receipts:manual.save")).click()
    expect(screen.get_by_role("status")).to_be_visible()

    with account.api() as api:
        stored = api.get("/receipts", params={"size": 10}).json()["items"]
    assert [(r["merchant_name"], Decimal(str(r["total_amount"]))) for r in stored] == [
        ("Таксі з вокзалу", Decimal("45.50"))
    ]


def test_the_ai_refused_says_why_and_is_allowed_from_the_refusal(screen: Page) -> None:
    account = register("consent")
    token = mail_link(account.email, "/confirm-email").split("token=")[1]
    httpx.post(f"{API_URL}/auth/confirm-email", json={"token": token}).raise_for_status()
    with account.api() as api:
        account.user = api.patch("/users/me", json={"currency": "PLN", "onboarded": True}).json()

    sign_in(screen, account, "/upload")
    # Asked on arrival; "not now" leaves the AI off.
    screen.get_by_role("button", name=words("profile:aiConsent.later")).click()
    screen.locator('input[type="file"][accept*="pdf"]:not([capture])').first.set_input_files(
        str(BIEDRONKA)
    )
    read = screen.get_by_role("button", name=words("upload:add.read"))
    read.click()
    expect(screen.get_by_text(words("errors:ai_consent_required"))).to_be_visible()
    shot(screen, "consent", "refused")

    screen.get_by_role("button", name=words("upload:add.allowAi")).click()
    screen.get_by_role("button", name=words("profile:aiConsent.allow"), exact=True).click()
    read.click()
    expect(screen.get_by_role("heading", name=words("upload:read.title"))).to_be_visible()
    shot(screen, "consent", "allowed")


def test_the_account_is_deleted_with_its_password_and_cannot_sign_in(screen: Page) -> None:
    account = ready_account("delete")
    sign_in(screen, account, "/settings")
    screen.get_by_role("button", name=words("profile:data.delete")).click()
    dialog = screen.get_by_role("dialog")
    dialog.get_by_label(words("profile:data.password")).fill(account.password)
    shot(screen, "delete", "dialog")
    dialog.get_by_role("button", name=words("profile:data.confirm")).click()
    expect(screen).to_have_url(f"{screen.url.split('/settings')[0]}/login", timeout=15_000)

    signed_in = httpx.post(
        f"{API_URL}/auth/login", json={"email": account.email, "password": account.password}
    )
    assert signed_in.status_code == 401
