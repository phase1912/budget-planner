"""Which addresses an account may be opened with (F17.8.4)."""

import pytest

from app.domain.email_addresses import disposable_domains, domain_of, is_disposable


def test_the_kept_list_names_the_well_known_throwaway_services() -> None:
    assert {"mailinator.com", "10minutemail.com"} <= disposable_domains()
    assert "gmail.com" not in disposable_domains()


@pytest.mark.parametrize("domain", ["mailinator.com", "x.mailinator.com", "a.b.mailinator.com"])
def test_a_throwaway_domain_is_refused_under_any_subdomain(domain: str) -> None:
    assert is_disposable(domain, {"mailinator.com"})


def test_a_domain_merely_ending_like_a_throwaway_one_is_not_refused() -> None:
    assert not is_disposable("notmailinator.com", {"mailinator.com"})
    assert not is_disposable("com", {"com"})


def test_the_domain_is_read_without_case_or_a_trailing_dot() -> None:
    assert domain_of("Ann@Mail.Example.COM.") == "mail.example.com"
