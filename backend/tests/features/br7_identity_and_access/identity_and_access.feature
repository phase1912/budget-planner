# BRD BR-7 — Identity & Access (docs/requirements/ai-budget-agent-brd-v1.1.md).
# Scenario wording is copied verbatim from the BRD so the two stay comparable;
# only the leading @-tags (BRD requirement IDs, F0.6.4's traceability report)
# are additions not present in the BRD itself.
Feature: Registration, authentication and identity linking

  @G1
  Scenario: Register a new account
    Given no account exists for "new.user@example.com"
    When the person registers with that email and a password
    Then the system should create the account
    And establish an authenticated session

  @G2
  Scenario: Reject registration with an email already in use
    Given an account already exists for "existing.user@example.com"
    When someone registers using that same email address
    Then the system should reject the registration
    And the response should not reveal that the address is already registered

  @G3
  Scenario: Log in with valid credentials
    Given a registered account with a known email and password
    When the person submits the correct email and password
    Then the system should authenticate them
    And establish a session

  @G4
  Scenario: Reject login with invalid credentials
    Given a registered account
    When the person submits an unknown email, or the correct email with the wrong password
    Then the system should return the same generic authentication error in both cases

  @G5
  Scenario: Refresh an expired access token
    Given the person has an authenticated session and an unexpired refresh token
    When their access token expires and they present the refresh token
    Then the system should issue a new access token
    And the person should not be required to log in again

  @G6
  Scenario: Detect reuse of an already-exchanged refresh token
    Given a refresh token that has already been exchanged once
    When that same refresh token is presented again
    Then the system should revoke every token issued from that session
    And require the person to log in again

  @G7
  Scenario: Log out revokes the session
    Given the person has an authenticated session
    When the person logs out
    Then the system should revoke that session's access and refresh tokens

  @G8
  Scenario: Administrator access does not extend to a user's financial data
    Given an administrator account and a separate user account with stored receipts
    When the administrator uses the product
    Then the administrator should not be able to read that user's receipts, line items or statistics

  @G9 @G10
  Scenario: Sign in via Google for the first time, linking to a matching verified account
    Given a registered account exists for "person@example.com"
    And Google reports "person@example.com" as a verified email for the signing-in identity
    When the person signs in with Google for the first time
    Then the system should link the Google identity to the existing account
    And establish an authenticated session

  @G9 @G11
  Scenario: Reject linking on an unverified provider email
    Given a registered account exists for "person@example.com"
    And Google reports "person@example.com" as an unverified email for the signing-in identity
    When the person attempts to sign in with Google for the first time
    Then the system should not link the Google identity to the existing account
    And should require an explicit verification step before linking

  @G12
  Scenario: Sign in with either a linked provider or a password
    Given an account with both a password and a linked Google identity
    When the person authenticates with the password, or separately with Google
    Then the system should authenticate them in either case
