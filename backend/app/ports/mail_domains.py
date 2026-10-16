"""Asking DNS whether a domain receives mail (F17.8.4)."""

from typing import Protocol


class MailDomainResolverPort(Protocol):
    """Whether mail sent to a domain can be delivered at all.

    Answers True when the domain has an MX record, or failing that an address record
    (mail then goes to the host itself); False when DNS says it has neither or does not
    exist; None when DNS could not be asked, which must never refuse anyone.
    """

    async def receives_mail(self, domain: str) -> bool | None: ...
