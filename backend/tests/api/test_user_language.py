"""The language a user reads the product in, kept with the account (F9.9)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.api.test_household import _call
from tests.factories.user import UserFactory


@pytest.mark.asyncio
async def test_a_new_account_has_not_chosen_a_language(db_session: AsyncSession) -> None:
    """The client then goes by the browser's language."""
    user = await UserFactory.create_async(language=None)

    assert (await _call(db_session, user, "GET", "/users/me")).json()["language"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["uk", "pl", "en"])
async def test_the_chosen_language_is_kept_with_the_account(
    db_session: AsyncSession, language: str
) -> None:
    user = await UserFactory.create_async(language=None)

    changed = await _call(db_session, user, "PATCH", "/users/me", {"language": language})
    read = await _call(db_session, user, "GET", "/users/me")

    assert (changed.status_code, read.json()["language"]) == (200, language)


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["ru", "de", "UK", ""])
async def test_a_language_the_product_is_not_written_in_is_refused(
    db_session: AsyncSession, language: str
) -> None:
    user = await UserFactory.create_async(language="uk")

    response = await _call(db_session, user, "PATCH", "/users/me", {"language": language})

    assert response.status_code == 422
    assert (await _call(db_session, user, "GET", "/users/me")).json()["language"] == "uk"
