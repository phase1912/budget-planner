# mypy: disable-error-code="no-untyped-def"
"""Runs BR-7's Gherkin scenarios (F0.10.1)."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.main import app
from app.session import get_db_session

scenarios("identity_and_access.feature")


@pytest.fixture
def auth_state():
    return {}


@pytest.fixture
def override_db(test_database_url):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(test_database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_db(test_database_url):
    # Clean the users table before each test to prevent unique constraint violations across tests
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.conftest import _run

    async def _clean() -> None:
        engine = create_async_engine(test_database_url)
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE users CASCADE"))
        await engine.dispose()

    _run(_clean())


@given(parsers.parse('no account exists for "{email}"'))
def no_account_exists(override_db, email):
    pass


@when(parsers.parse("the person registers with that email and a password"))
def register_account(auth_state, override_db, email="new.user@example.com"):
    client = TestClient(app)
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "securepassword",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    auth_state["response"] = response


@then("the system should create the account")
def account_created(auth_state):
    response = auth_state.get("response")
    assert response is not None
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["user"]["email"] == "new.user@example.com"


@then("establish an authenticated session")
def session_established(auth_state):
    response = auth_state.get("response")
    data = response.json()
    assert "access_token" in data


@given(parsers.parse('an account already exists for "{email}"'))
@given(parsers.parse('a registered account exists for "{email}"'))
def account_already_exists(auth_state, override_db, email):
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "securepassword",
            "first_name": "Test",
            "last_name": "User",
        },
    )


@when("someone registers using that same email address")
def register_duplicate(auth_state, override_db):
    client = TestClient(app)
    response = client.post(
        "/auth/register",
        json={
            "email": "existing.user@example.com",
            "password": "anotherpassword",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    auth_state["response"] = response


@then("the system should reject the registration")
def registration_rejected(auth_state):
    assert auth_state["response"].status_code == status.HTTP_400_BAD_REQUEST


@then("the response should not reveal that the address is already registered")
def not_reveal_registration(auth_state):
    data = auth_state["response"].json()
    assert "already registered" not in data.get("detail", "").lower()
    assert data["code"] == "registration_failed"


@given("a registered account with a known email and password")
def existing_account(auth_state, override_db):
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        },
    )


@when("the person submits the correct email and password")
def login_correct(auth_state, override_db):
    client = TestClient(app)
    response = client.post(
        "/auth/login", json={"email": "user@example.com", "password": "SecurePass123!"}
    )
    auth_state["response"] = response


@then("the system should authenticate them")
def authenticate_them(auth_state):
    assert auth_state["response"].status_code == status.HTTP_200_OK


@then("establish a session")
def login_session_established(auth_state):
    data = auth_state["response"].json()
    assert "access_token" in data


@given("a registered account")
def registered_account(auth_state, override_db):
    client = TestClient(app)
    client.post("/auth/register", json={"email": "test@example.com", "password": "SecurePass123!"})


@when("the person submits an unknown email, or the correct email with the wrong password")
def login_invalid(auth_state, override_db):
    client = TestClient(app)
    response_wrong_email = client.post(
        "/auth/login", json={"email": "unknown@example.com", "password": "SecurePass123!"}
    )
    response_wrong_pass = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "wrongpassword"}
    )
    auth_state["response_wrong_email"] = response_wrong_email
    auth_state["response_wrong_pass"] = response_wrong_pass


@then("the system should return the same generic authentication error in both cases")
def generic_auth_error(auth_state):
    resp_e = auth_state["response_wrong_email"]
    resp_p = auth_state["response_wrong_pass"]
    assert resp_e.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp_p.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp_e.json() == resp_p.json()
    assert resp_e.json()["code"] == "authentication_failed"


# --- Stubs for unimplemented E1.2/E10/OIDC scenarios ---
@given("the person has an authenticated session and an unexpired refresh token")
def stub_g5():
    pytest.skip("Refresh token flow not implemented yet (E1.2)")


@when("their access token expires and they present the refresh token")
def stub_g5_1():
    pass


@then("the system should issue a new access token")
def stub_g5_2():
    pass


@then("the person should not be required to log in again")
def stub_g5_3():
    pass


@given("a refresh token that has already been exchanged once")
def stub_g6():
    pytest.skip("Refresh token rotation not implemented yet (E1.2)")


@when("that same refresh token is presented again")
def stub_g6_1():
    pass


@then("the system should revoke every token issued from that session")
def stub_g6_2():
    pass


@then("require the person to log in again")
def stub_g6_3():
    pass


@given("the person has an authenticated session")
def stub_g7():
    pytest.skip("Logout flow not implemented yet (E1.2)")


@when("the person logs out")
def stub_g7_1():
    pass


@then("the system should revoke that session's access and refresh tokens")
def stub_g7_2():
    pass


@given("an administrator account and a separate user account with stored receipts")
def stub_g8():
    pytest.skip("Admin role not implemented yet")


@when("the administrator uses the product")
def stub_g8_1():
    pass


@then("the administrator should not be able to read that user's receipts, line items or statistics")
def stub_g8_2():
    pass


@given(parsers.parse('Google reports "{email}" as a verified email for the signing-in identity'))
def stub_g9_1(email):
    pytest.skip("Google OIDC not implemented yet")


@when("the person signs in with Google for the first time")
def stub_g9_2():
    pass


@then("the system should link the Google identity to the existing account")
def stub_g9_3():
    pass


@given(parsers.parse('Google reports "{email}" as an unverified email for the signing-in identity'))
def stub_g11_1(email):
    pytest.skip("Google OIDC not implemented yet")


@when("the person attempts to sign in with Google for the first time")
def stub_g11_2():
    pass


@then("the system should not link the Google identity to the existing account")
def stub_g11_3():
    pass


@then("should require an explicit verification step before linking")
def stub_g11_4():
    pass


@given("an account with both a password and a linked Google identity")
def stub_g12_1():
    pytest.skip("Google OIDC not implemented yet")


@when("the person authenticates with the password, or separately with Google")
def stub_g12_2():
    pass


@then("the system should authenticate them in either case")
def stub_g12_3():
    pass
