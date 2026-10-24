"""A family keeping one budget (F0.11.4, E12): an invite opened, joined, and what one
member spends seen by the other on the family's month."""

import re
from datetime import date

from playwright.sync_api import Browser, Page, expect

from tests.e2e.helpers import ready_account, shot, sign_in, words


def test_a_member_joins_by_the_invite_and_their_spending_shows_for_the_family(
    screen: Page, browser: Browser, width: int
) -> None:
    owner = ready_account("owner")
    member = ready_account("member")
    with owner.api() as api:
        family = api.post("/api/v1/household", json={"name": "Тестова родина"})
        family.raise_for_status()
        code = family.json()["invite_code"]

    sign_in(screen, member, f"/join/{code}")
    screen.get_by_role("button", name=words("household:join.join", name="Тестова родина")).click()
    # Joined, the new member lands in Settings, where the family is.
    expect(screen).to_have_url(re.compile(r"/settings$"))
    shot(screen, "family", "joined")
    with member.api() as api:
        api.post(
            "/receipts/manual",
            json={
                "description": "Продукти на вихідні",
                "spent_on": date.today().isoformat(),
                "amount": "120.00",
                "category_id": "00000000-0000-0000-0000-000000000001",
            },
        ).raise_for_status()

    # The owner on a device of their own, as a family uses it.
    device = browser.new_context(viewport={"width": width, "height": 900}, locale="uk-UA")
    home = device.new_page()
    try:
        sign_in(home, owner, "/")
        home.get_by_text(words("common:household"), exact=True).first.click()
        expect(home.get_by_text(words("dashboard:household.spentTogether")).first).to_be_visible()
        shot(home, "family", "owner-sees-family")
    finally:
        shot(home, "family", "owner-last")
        device.close()

    with owner.api() as api:
        members = api.get("/api/v1/household").json()["members"]
    assert sorted(m["email"] for m in members) == sorted([owner.email, member.email])
