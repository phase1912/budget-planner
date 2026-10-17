"""How visits are counted without saying who (F17.3.2)."""

import pytest

from app.domain.activity import DIRECT, is_bot, visit_source

OWN = "budget-agent.web.app"


@pytest.mark.parametrize(
    ("referrer", "utm", "source"),
    [
        ("https://www.google.com/search?q=budget+app", None, "google"),
        ("https://www.google.pl/", None, "google"),
        ("https://l.instagram.com/?u=https%3A%2F%2Fbudget-agent.web.app", None, "instagram"),
        ("https://lm.facebook.com/l.php?u=x", None, "facebook"),
        ("android-app://com.instagram.android/", None, "instagram"),
        ("https://t.co/abc", None, "x"),
        ("https://blog.example.org/post", None, "blog.example.org"),
        ("https://budget-agent.web.app/help", None, DIRECT),
        (None, None, DIRECT),
        ("https://t.co/abc", "Telegram Channel!", "telegramchannel"),
        ("not a url", None, DIRECT),
    ],
)
def test_a_visit_is_kept_as_a_domain_or_a_campaign_never_a_full_address(
    referrer: str | None, utm: str | None, source: str
) -> None:
    assert visit_source(referrer, utm, OWN) == source


@pytest.mark.parametrize(
    "agent",
    ["Googlebot/2.1", "facebookexternalhit/1.1", "curl/8.5", "HeadlessChrome/120", None, ""],
)
def test_crawlers_and_tools_are_not_counted(agent: str | None) -> None:
    assert is_bot(agent)


def test_a_phones_browser_is_counted() -> None:
    assert not is_bot("Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) Safari/604.1")
