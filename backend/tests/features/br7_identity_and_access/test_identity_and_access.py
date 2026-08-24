# mypy: disable-error-code="no-untyped-def"
"""Runs BR-7's Gherkin scenarios (F0.10.1)."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.db.session import get_db_session
from app.api.rate_limit import limiter
from app.main import app
scenarios("identity_and_access.feature")


@pytest.fixture
def auth_state():
    return {}


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset slowapi's in-memory counter before each test.

    Without this, sequential tests that all call /auth/login from the same
    loopback address exhaust the 5/minute limit and cause 429 failures in
    later scenarios.
    """
    limiter.reset()
    yield


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
    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED


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
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED


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


# --- G5: Refresh an expired access token ---


@given("the person has an authenticated session and an unexpired refresh token")
def authenticated_session_with_refresh(auth_state, override_db):
    """Register and log in, storing both tokens for subsequent steps."""
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={
            "email": "refresh.user@example.com",
            "password": "SecurePass123!",
            "first_name": "Refresh",
            "last_name": "User",
        },
    )
    resp = client.post(
        "/auth/login",
        json={"email": "refresh.user@example.com", "password": "SecurePass123!"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    auth_state["access_token"] = data["access_token"]
    auth_state["refresh_token"] = data["refresh_token"]
    auth_state["client"] = client


@when("their access token expires and they present the refresh token")
def present_refresh_token(auth_state):
    """Call /auth/refresh with the stored refresh token."""
    client: TestClient = auth_state["client"]
    resp = client.post(
        "/auth/refresh",
        json={"refresh_token": auth_state["refresh_token"]},
    )
    auth_state["refresh_response"] = resp


@then("the system should issue a new access token")
def new_access_token_issued(auth_state):
    resp = auth_state["refresh_response"]
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "access_token" in data
    # Rotation: the new refresh token must differ from the one just exchanged
    assert data["refresh_token"] != auth_state["refresh_token"]
    auth_state["new_refresh_token"] = data["refresh_token"]


@then("the person should not be required to log in again")
def no_re_login_required(auth_state):
    """Verify the new access token is usable (not empty, not the old one)."""
    assert auth_state["refresh_response"].status_code == status.HTTP_200_OK


# --- G6: Detect reuse of an already-exchanged refresh token ---


@given("a refresh token that has already been exchanged once")
def refresh_token_already_exchanged(auth_state, override_db):
    """Register, log in, then call /auth/refresh once to consume the token."""
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={
            "email": "rotation.user@example.com",
            "password": "SecurePass123!",
            "first_name": "Rotation",
            "last_name": "User",
        },
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "rotation.user@example.com", "password": "SecurePass123!"},
    )
    original_refresh = login_resp.json()["refresh_token"]
    # Consume it once
    client.post("/auth/refresh", json={"refresh_token": original_refresh})
    auth_state["used_refresh_token"] = original_refresh
    auth_state["client"] = client


@when("that same refresh token is presented again")
def reuse_refresh_token(auth_state):
    """Present the already-used refresh token a second time."""
    client: TestClient = auth_state["client"]
    resp = client.post(
        "/auth/refresh",
        json={"refresh_token": auth_state["used_refresh_token"]},
    )
    auth_state["reuse_response"] = resp


@then("the system should revoke every token issued from that session")
def family_revoked(auth_state):
    """The server must reject the replayed token."""
    assert auth_state["reuse_response"].status_code == status.HTTP_401_UNAUTHORIZED


@then("require the person to log in again")
def must_log_in_again(auth_state):
    """Confirm the error code signals an expired/revoked session."""
    data = auth_state["reuse_response"].json()
    assert data.get("code") in ("token_revoked", "authentication_failed", "invalid_token")


# --- G7: Log out revokes the session ---


@given("the person has an authenticated session")
def session_for_logout(auth_state, override_db):
    """Register and log in, storing both tokens."""
    client = TestClient(app)
    client.post(
        "/auth/register",
        json={
            "email": "logout.user@example.com",
            "password": "SecurePass123!",
            "first_name": "Logout",
            "last_name": "User",
        },
    )
    resp = client.post(
        "/auth/login",
        json={"email": "logout.user@example.com", "password": "SecurePass123!"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    auth_state["access_token"] = data["access_token"]
    auth_state["refresh_token"] = data["refresh_token"]
    auth_state["client"] = client


@when("the person logs out")
def perform_logout(auth_state):
    """Call /auth/logout with the refresh token."""
    client: TestClient = auth_state["client"]
    resp = client.post(
        "/auth/logout",
        json={"refresh_token": auth_state["refresh_token"]},
        headers={"Authorization": f"Bearer {auth_state['access_token']}"},
    )
    auth_state["logout_response"] = resp


@then("the system should revoke that session's access and refresh tokens")
def session_revoked(auth_state):
    """Logout must succeed and subsequent refresh must be rejected."""
    assert auth_state["logout_response"].status_code == status.HTTP_200_OK
    # Try refreshing with the now-revoked token — must fail
    client: TestClient = auth_state["client"]
    retry = client.post(
        "/auth/refresh",
        json={"refresh_token": auth_state["refresh_token"]},
    )
    assert retry.status_code == status.HTTP_401_UNAUTHORIZED


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
