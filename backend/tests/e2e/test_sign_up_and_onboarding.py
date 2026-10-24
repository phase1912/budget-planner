"""Signing up, the setup that follows, and confirming the address (F0.11.4, F17.8, F23.9).

Includes the first outside tester's case (F24.3): an income typed into onboarding and
left with Next instead of its own Save is saved, and the summary shows it and its card.
"""

import re

from playwright.sync_api import Page, expect

from tests.e2e.helpers import BASE_URL, mail_link, new_email, shot, words


def test_a_new_user_signs_up_sets_up_and_confirms_the_address(screen: Page) -> None:
    page = screen
    email = new_email("signup")
    page.goto(f"{BASE_URL}/register")
    page.get_by_label(words("auth:fields.firstName")).fill("Олена")
    page.get_by_label(words("auth:fields.lastName")).fill("Тестова")
    page.get_by_label(words("auth:fields.email")).fill(email)
    page.get_by_label(words("auth:fields.password"), exact=True).fill("Kotyk-Na-Dyvani-42")
    page.get_by_label(words("auth:fields.confirmPassword")).fill("Kotyk-Na-Dyvani-42")
    page.get_by_role("checkbox").check()
    shot(page, "signup", "form")
    page.get_by_role("button", name=words("auth:register.submit")).click()

    # The setup, as the tester went through it: no card on its own step, an income
    # with "what is on the card now", left with Next.
    page.get_by_role("button", name=words("onboarding:welcome.start")).click()
    page.get_by_role("button", name="USD", exact=True).click()
    next_step = page.get_by_role("button", name=words("onboarding:next"), exact=True)
    next_step.click()
    next_step.click()
    next_step.click()
    page.get_by_role("button", name=words("profile:regular.addFirst")).click()
    page.get_by_label(words("profile:regular.name")).fill("Зарплата")
    page.get_by_label(words("profile:regular.amount", currency="USD")).fill("1000")
    page.get_by_label(words("accounts:newCard.opening", currency="USD")).fill("1000")
    shot(page, "signup", "income")
    next_step.click()
    expect(page.get_by_role("radio").first).to_be_visible()
    next_step.click()
    next_step.click()

    summary = page.locator("dl")
    expect(summary).to_contain_text(re.compile(r"1\s000\sUSD"))
    expect(summary).not_to_contain_text(words("onboarding:income.none"))
    shot(page, "signup", "summary")
    page.get_by_role("button", name=words("onboarding:done.look")).click()

    banner = page.get_by_text(words("auth:banner.short", email=email)).or_(
        page.get_by_text(words("auth:banner.text", email=email))
    )
    # A phone shows the short wording, wider screens the long one.
    expect(banner.filter(visible=True)).to_be_visible()
    shot(page, "signup", "home-unconfirmed")

    page.goto(mail_link(email, "/confirm-email"))
    expect(page.get_by_text(words("auth:confirm.done"))).to_be_visible()
    page.goto(f"{BASE_URL}/")
    expect(page.get_by_text(words("auth:banner.short", email=email))).to_have_count(0)
    expect(page.get_by_text(words("auth:banner.text", email=email))).to_have_count(0)
    shot(page, "signup", "home-confirmed")
