"""What the browser suite needs besides the browser (F0.11.1): the API, the local mail
log, the product's own words, and screenshots."""

import json
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import httpx
from playwright.sync_api import Page

REPO = Path(__file__).resolve().parents[3]
LOCALES = REPO / "frontend" / "src" / "locales"
SCREENS = REPO / "backend" / "e2e-results" / "screens"
API_URL = os.environ.get("E2E_API_URL", "http://localhost:8000")
BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:5173")


@cache
def _locale(language: str, area: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (LOCALES / language / f"{area}.json").read_text(encoding="utf-8")
    )
    return data


def words(key: str, language: str = "uk", **values: str) -> str:
    """The product's text for `area:dotted.key` in a language, filled like i18next does."""
    area, _, path = key.partition(":")
    node: Any = _locale(language, area)
    for part in path.split("."):
        node = node[part]
    text = str(node)
    for name, value in values.items():
        text = text.replace("{{" + name + "}}", value)
    return text


def mail_link(email: str, path: str) -> str:
    """The latest link to `path` (e.g. "/confirm-email") in a letter to `email`.

    Locally letters are written to the backend's log (ADR-0019); this reads it the way a
    person reads their mailbox.
    """
    log = subprocess.run(
        ["docker", "compose", "logs", "backend", "--since", "30m", "--no-log-prefix"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    letters = log.split("Letter to ")
    for letter in reversed(letters):
        if letter.startswith(email):
            found = re.search(rf"https?://\S+{re.escape(path)}\?token=[\w.-]+", letter)
            if found:
                return found.group(0)
    raise AssertionError(f"No letter to {email} with a {path} link in the backend log")


@dataclass
class Account:
    """A user made for one test, with a live session."""

    email: str
    password: str
    access_token: str
    refresh_token: str
    user: dict[str, Any]

    def api(self) -> httpx.Client:
        """An API client signed in as this account."""
        return httpx.Client(
            base_url=API_URL,
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30,
        )


def new_email(label: str) -> str:
    return f"e2e-{label}-{uuid.uuid4().hex[:10]}@example.com"


def register(label: str, language: str = "uk") -> Account:
    """A new account through the API, as the sign-up form makes it: unconfirmed."""
    email = new_email(label)
    password = f"E2e-{uuid.uuid4().hex[:12]}!"
    response = httpx.post(
        f"{API_URL}/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "Тест",
            "last_name": "Користувач",
            "accept_terms": True,
            "language": language,
        },
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    return Account(email, password, body["access_token"], body["refresh_token"], body["user"])


def ready_account(label: str, *, currency: str = "PLN", language: str = "uk") -> Account:
    """An account past every gate: address confirmed, AI allowed, onboarding done."""
    account = register(label, language)
    token = mail_link(account.email, "/confirm-email").split("token=")[1]
    httpx.post(
        f"{API_URL}/auth/confirm-email", json={"token": token}, timeout=30
    ).raise_for_status()
    with account.api() as api:
        api.put("/users/me/ai-consent", json={"given": True}).raise_for_status()
        done = api.patch("/users/me", json={"currency": currency, "onboarded": True})
        done.raise_for_status()
        account.user = done.json()
    return account


def sign_in(page: Page, account: Account, path: str = "/") -> None:
    """Open `path` already signed in, as a returning user would."""
    page.goto(f"{BASE_URL}/login")
    page.evaluate(
        """([access, refresh, user]) => {
            localStorage.setItem("budget_access_token", access);
            localStorage.setItem("budget_refresh_token", refresh);
            localStorage.setItem("budget_user", user);
        }""",
        [account.access_token, account.refresh_token, json.dumps(account.user)],
    )
    page.goto(f"{BASE_URL}{path}")


def shot(page: Page, test: str, name: str) -> Path:
    """Keep a screenshot to look at after the run, named by test, width and moment."""
    width = page.viewport_size["width"] if page.viewport_size else 0
    path = SCREENS / f"{test}-{width}-{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=True)
    return path
