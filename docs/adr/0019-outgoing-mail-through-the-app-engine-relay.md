# ADR 0019: Account letters go out through the App Engine relay's Mail API

**Date:** 2026-10-16
**Status:** Accepted

## Context

F17.8 makes an account belong to an address its owner reads: sign-up sends a link that
confirms it, a forgotten password is reset through a link, and a new address is switched
to only once a link sent to it is followed. That needs outgoing mail. Every SMTP or API
provider (Resend, SendGrid, Mailgun, Mailjet, SES) needs a domain the project owns to
send from without landing in spam, and the project has no domain and buys nothing
before it has traffic (E19).

The App Engine app that already receives forwarded receipts (ADR-0013) can also send:
the legacy bundled Mail API lets it send from `anything@<project>.appspotmail.com`
without a domain. The API is callable only from inside App Engine, and Google marks it
legacy, recommending SMTP providers for reliable high-volume delivery.

## Decision

- **A port, `EmailSenderPort`** (`app/ports/email.py`), with one method that hands a
  plain-text letter over or raises `EmailSendError`. Services never name a provider.
- **The relay gains `POST /send`**, authenticated by the same shared secret as inbound
  mail (`X-Relay-Secret` = `INBOUND_EMAIL_SECRET`), which calls `mail.send_mail` from
  `Budget Agent <noreply@<project>.appspotmail.com>`. The backend's
  `AppEngineMailSender` posts to `https://<project>.appspot.com/send`, derived from
  `INBOUND_EMAIL_DOMAIN`, so the deployment needs no new setting or secret.
- **Locally and in tests** `LogMailSender` writes the letter, link included, to the
  backend's log; tests stub the Mailer and read the letters it was given.
- **Sending never fails the request that caused it.** Letters are delivered in a
  FastAPI background task by `Mailer`, which retries three times (2, 10 and 30 seconds:
  the relay may be starting cold) and then logs the failure. The screen always offers
  to send a confirmation link again.
- **Links are signed, expiring tokens** (24 hours to confirm an address, one hour to
  reset a password) bound to the state they change — the address, a fingerprint of the
  password hash — so each works once without a table of spent links. They carry a
  `purpose` claim, and a token with one is never accepted as a session.
- **A letter may name a Reply-To** (`Letter.reply_to`, passed to `send_mail`): the contact
  form's messages (F17.10) are answered straight to the person who wrote, since the
  sender address is nobody's inbox.
- **Letters are written in the reader's language** (English, Ukrainian, Polish), from
  `app/domain/letters.py`; at sign-up and on "forgot password", the language of the
  screen the request came from.

## Quota

The Mail API's daily recipient quota is not published in the documentation; it is shown
on the project's Quotas page in the Cloud console (App Engine → Quotas → Mail). Community
reports put the default at about 100 recipients a day, ample for the diploma's users.
**Check the console figure before inviting users and record it here.** Exceeding it
raises an over-quota error in the relay; the backend retries, then logs, and the user can
ask for the letter again the next day.

## Consequences

- No domain, no account with a mail provider, no cost.
- Letters come from an `appspotmail.com` address without the project's own DKIM, so some
  may land in spam; the confirmation banner says where the link was sent and offers to
  resend.
- Replacing the Mail API — when a domain is bought (E19), or if Google retires the
  legacy API — is one adapter (for example Resend over HTTPS) behind `EmailSenderPort`,
  and removing `/send` from the relay.
