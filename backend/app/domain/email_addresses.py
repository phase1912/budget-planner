"""Which addresses an account may be opened with (F17.8.4)."""

from collections.abc import Collection
from functools import cache
from pathlib import Path

_BLOCKLIST = Path(__file__).with_name("disposable_email_domains.txt")


@cache
def disposable_domains() -> frozenset[str]:
    """The throwaway email domains kept in the repository, read once per process."""
    lines = _BLOCKLIST.read_text(encoding="utf-8").splitlines()
    return frozenset(line for line in lines if line and not line.startswith("#"))


def domain_of(email: str) -> str:
    """The part after the @, lower-cased and without a trailing dot."""
    return email.rsplit("@", 1)[-1].strip().lower().rstrip(".")


def is_disposable(domain: str, blocklist: Collection[str]) -> bool:
    """Whether a domain, or any domain it is under, gives out throwaway addresses.

    `x.mailinator.com` is as throwaway as `mailinator.com`: services hand out
    subdomains precisely to slip past lists of exact names.
    """
    parts = domain.split(".")
    return any(".".join(parts[i:]) in blocklist for i in range(len(parts) - 1))
