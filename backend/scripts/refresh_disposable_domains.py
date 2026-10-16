"""Refresh the list of throwaway email domains refused at sign-up (F17.8.4).

The list is the community-maintained disposable-email-domains blocklist (CC0), kept in
the repository so sign-up never asks a third party about an address:

    uv run python scripts/refresh_disposable_domains.py

Commit the changed file; review the diff for anything that looks like a real provider.
"""

import sys
import urllib.request
from pathlib import Path

SOURCE = (
    "https://raw.githubusercontent.com/disposable-email-domains/disposable-email-domains"
    "/main/disposable_email_blocklist.conf"
)
TARGET = Path(__file__).resolve().parents[1] / "app/domain/disposable_email_domains.txt"
HEADER = (
    "# Throwaway email domains refused at sign-up (F17.8.4).\n"
    "# From disposable-email-domains/disposable-email-domains (CC0); refresh with\n"
    "# scripts/refresh_disposable_domains.py rather than editing by hand.\n"
)


def main() -> int:
    """Download the blocklist and write it, sorted and lower-cased, over the kept copy."""
    with urllib.request.urlopen(SOURCE, timeout=30) as response:
        text = response.read().decode("utf-8")
    domains = sorted(
        {line.strip().lower() for line in text.splitlines() if line.strip() and "#" not in line}
    )
    if len(domains) < 1000:
        print(f"Only {len(domains)} domains downloaded; keeping the current list.")
        return 1
    TARGET.write_text(HEADER + "\n".join(domains) + "\n", encoding="utf-8")
    print(f"Wrote {len(domains)} domains to {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
