"""The browser suite's fixtures (F0.11.1): skipped unless pointed at a running stack."""

import os
import shutil
from collections.abc import Generator, Iterator

import pytest
from playwright.sync_api import Browser, Page

from tests.e2e.helpers import SCREENS

WIDTHS = {"phone": 375, "tablet": 768, "desktop": 1280}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Without E2E_BASE_URL the suite is skipped: the unit run has no stack or browser."""
    if os.environ.get("E2E_BASE_URL"):
        return
    skip = pytest.mark.skip(reason="the browser suite runs with scripts/e2e.sh (F0.11)")
    for item in items:
        if "tests/e2e/" in str(item.fspath):
            item.add_marker(skip)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Note on each test whether its run failed, for the screenshot below."""
    report = yield
    if report is not None and report.when == "call":
        item.stash[FAILED] = report.failed
    return report


FAILED = pytest.StashKey[bool]()


def _keep_failure(request: pytest.FixtureRequest, page: Page) -> None:
    """A failed test leaves the screen it failed on, next to the run's screenshots."""
    if request.node.stash.get(FAILED, False):
        SCREENS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENS / f"FAILED-{request.node.name}.png"), full_page=True)


@pytest.fixture(scope="session", autouse=True)
def fresh_screens() -> None:
    """Each run's screenshots alone, so what is looked at afterwards is this run's."""
    if os.environ.get("E2E_BASE_URL"):
        shutil.rmtree(SCREENS, ignore_errors=True)


@pytest.fixture(params=list(WIDTHS), ids=list(WIDTHS))
def width(request: pytest.FixtureRequest) -> int:
    """Each flow runs on a phone, a tablet and a desktop (CLAUDE.md)."""
    return WIDTHS[request.param]


@pytest.fixture
def screen(request: pytest.FixtureRequest, browser: Browser, width: int) -> Iterator[Page]:
    """A fresh page at the flow's width, in Ukrainian, with nothing remembered."""
    context = browser.new_context(
        viewport={"width": width, "height": 900},
        locale="uk-UA",
        is_mobile=width < 768 and browser.browser_type.name == "chromium",
        has_touch=width < 768,
    )
    page = context.new_page()
    page.set_default_timeout(15_000)
    yield page
    _keep_failure(request, page)
    context.close()


@pytest.fixture
def phone(request: pytest.FixtureRequest, browser: Browser) -> Iterator[Page]:
    """A phone page, for the corpus cases: reading does not depend on the width."""
    context = browser.new_context(viewport={"width": 375, "height": 900}, locale="uk-UA")
    page = context.new_page()
    page.set_default_timeout(15_000)
    yield page
    _keep_failure(request, page)
    context.close()
