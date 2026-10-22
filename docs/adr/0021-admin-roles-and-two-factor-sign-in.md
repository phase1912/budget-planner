# ADR 0021: Admin roles, two-factor sign-in and granted plans

**Date:** 2026-10-17
**Status:** Accepted

## Context

Running the service meant opening the database: confirming a stuck address, giving a
tester more receipt reads. F18.6 moves that into an admin console. An admin account can
change other accounts, so it is worth more to an attacker than any other — a password
alone should not open it. Plans (F18.2, F18.4) arrive before payments (F18.3), so the
first paid plans are ones an admin grants.

## Decision

**Two kinds of admin.** A *super admin* is an address in `admin_emails` — the operator
and his wife — set by the deployment and changeable nowhere else. An *admin* is
`role = "admin"` on the account, appointed and removed only by a super admin, never by
another admin and never by themselves. Admins see account facts and activity, act for
the account (confirm the address, send the confirmation or a reset link, grant or take
back a plan), and see none of its receipts (N2). They never set a password: they send
the owner a link.

**Two-factor sign-in (TOTP, RFC 6238).** An authenticator app, set up by QR code, with
10 single-use recovery codes stored as SHA-256 hashes. Any account may turn it on in
Preferences; an admin page refuses (403 `second_factor_required`) a session not opened
with it. Chosen over codes by email because the mailbox is often what an attacker
already has, and over passkeys because one TOTP secret works on any device and in the
Android app (E22) with no platform work. A deployment can switch the requirement off
(`ADMIN_SECOND_FACTOR_REQUIRED`); it is off by default only locally.

- With it on, `/auth/login` answers a five-minute challenge, bound to the password's
  fingerprint, not a session; `/auth/login/second-factor` exchanges it and a code for one.
- The session carries the fact as a claim (`sf`) in the access token and a flag on the
  refresh token, so refreshing keeps it and it never has to be asked for again mid-session.
- Turning it on returns a fresh second-factor session, so an admin need not sign in again.
- Turning it off needs the password and a current code.
- Every sign-in of an admin account is mailed to its address, so a stranger's is seen.

**The secret is encrypted** with Fernet under a key derived from `JWT_SECRET_KEY`
(SHA-256 of a fixed label and the secret), not stored in clear: a database dump alone
does not give the codes. One secret to manage instead of two; the price is that rotating
the JWT secret voids every authenticator, and their owners set them up again (recovery
codes still sign them in).

**Granted plans.** A grant gives the paid plan from a start to an end, with a reason
and who granted it. A grant made while a plan runs starts when that one ends, so
"30 more days" means that; the plan in force runs on through grants that follow each
other without a gap. Taking a grant back keeps its row with `revoked_at`. Payments
(F18.3) will add subscriptions beside grants, read the same way.

**The admin log.** Every admin action is a row — who, to whom, what, details such as the
reason — read only by super admins. Deleting either account leaves the entry with that
side gone.

## Consequences

- An admin needs a phone with an authenticator app; a lost phone is a recovery code.
- Rotating `JWT_SECRET_KEY` now also resets every two-factor setup; the runbook says so.
- A new admin action is added to `AdminActionKind` and written to the log, or it is not
  done through the console.
- The plan, not one setting, sets the limit: since F21.9 (ADR-0030) a monthly wallet of AI
  credits, `free_monthly_credits` (free) and `paid_monthly_credits` (paid).
