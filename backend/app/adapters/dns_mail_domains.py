"""DNS lookups behind MailDomainResolverPort (F17.8.4)."""

import dns.asyncresolver
import dns.exception
import dns.resolver


class DnsMailDomainResolver:
    """Looks up MX, then A and AAAA, with a short timeout: sign-up must not hang on DNS."""

    def __init__(self, timeout: float = 3.0) -> None:
        self.timeout = timeout

    async def receives_mail(self, domain: str) -> bool | None:
        undecided = False
        for record in ("MX", "A", "AAAA"):
            try:
                await dns.asyncresolver.resolve(domain, record, lifetime=self.timeout)
                return True
            except dns.resolver.NXDOMAIN:
                return False
            except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):
                continue
            except dns.exception.DNSException:
                undecided = True
        return None if undecided else False
