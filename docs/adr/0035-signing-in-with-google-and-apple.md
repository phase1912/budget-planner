# ADR 0035: Signing in with Google and Apple

**Date:** 2026-10-24
**Status:** Accepted — F1.6. Built and switched off until the client ids are configured.

## Context

On a phone, a password plus a confirmation letter is the slowest way into the service. F1.6
asks for Google and Apple through OpenID Connect, without ever linking an account silently.
App Review 4.8 asks for Apple wherever Google is offered in the iOS app. The keys come from
the owner's Google Cloud and Apple Developer accounts, which do not exist yet. So the feature
has to be built, tested and kept off until they do.

## Decision

### Trust and storage

- **The server trusts only the ID token, checked against the provider's own keys.**
  - Google's and Apple's tokens are verified with the key set each publishes (JWKS, RS256).
  - The checks: issuer, audience (one of our client ids), expiry and the nonce the client asked with.
  - Apple's native sign-in sends the nonce's SHA-256, so either form is accepted for Apple.
  - Behind a port (`IdTokenVerifierPort`), so the tests sign tokens with their own key set and run the real checks without the network.
- **A provider account is a row, linked to one user.**
  - `linked_identities` holds the provider, its stable `subject`, the address it gave and which of our client ids the token was issued to.
  - Unique per (provider, subject) and per (user, provider).
  - Deleting the account deletes the rows by cascade.

### Accounts

- **New, existing and signed-in accounts.**
  - **New:** a provider-confirmed address opens a new account, confirmed at once, with the terms accepted on the same screen.
  - **Existing:** an address that already has an account needs that account's password once (`link_needs_password`). Only then is the provider linked.
  - **Signed in:** linking happens from Settings while signed in. A provider account already linked elsewhere is refused (`identity_taken`, BRD N2).
- **Accounts without a password.**
  - An account opened through a provider has `password_set = false` and a hash of a random secret nobody knows.
  - A reset link sets a real password. Settings offers to send one.
  - Until then, unlinking the last provider is refused (`last_way_in`).
  - Deleting the account is confirmed by typing its address.
- **Two-factor sign-in still applies.** A provider sign-in to an account with an authenticator goes through the same code step as a password (`AuthService.open_session`).

### The website

- **The browser goes to the provider and back.**
  - **Google:** Google's own page answers into the address's fragment (`response_type=id_token`).
  - **Apple:** Apple posts to `/auth/apple/callback` (`form_post`, required when Apple shares the name). The server only redirects that post into the client's fragment.
- **Nothing from the providers is loaded into the page.** No script, no cookie, nothing from their origins:
  - a random `state` and `nonce` live in `sessionStorage` for that one trip;
  - `lint:privacy` lists both sign-in pages as places the user is sent, never loaded from.

### Apple's rules (App Review 5.1.1)

- With a sign-in's authorization code, the server keeps Apple's refresh token, encrypted.
- Deleting the account revokes it at Apple.
- Apple's server-to-server notifications (`/auth/apple/notifications`) for withdrawn consent or a deleted Apple ID unlink Apple.
- The client secret is a five-minute ES256 JWT made per call from the `.p8` key in Secret Manager. Nothing long-lived is stored, and there is no rotation to schedule.

### Switched off without keys

- No client ids means `GET /auth/providers` answers nulls, the buttons stay hidden, and `/auth/oidc/{provider}` answers 404 `sign_in_provider_off`.
- Terraform has the variables and the Apple key's secret ready (`infra/terraform/sign_in.tf`), all empty.

## Consequences

- **Not in the store apps yet.**
  - Google refuses OAuth inside an app's web view, so the apps do not show the buttons.
  - The native sign-ins wait for the keys: AuthenticationServices on iOS, Credential Manager on Android. They need the Sign in with Apple entitlement and Google's iOS client id in `Info.plist`.
  - The server already accepts their tokens: the bundle id is one of the Apple audiences.
- **ADR-0020 and the privacy policy** list the linked identities and Apple's encrypted token.
- **Turning it on:**
  1. Create a Google OAuth web client.
  2. Create an Apple Services ID with its return URL `<api>/auth/apple/callback`.
  3. Create an Apple key.
  4. Set the variables and add the key's version.
  5. Apply.
