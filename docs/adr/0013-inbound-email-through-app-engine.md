# ADR 0013: Emailed receipts arrive through App Engine's inbound mail

**Date:** 2026-10-08
**Status:** Accepted

## Context

F11.2 lets a user forward a shop's e-receipt to a personal address and find it on
Receipts. Receiving mail needs a domain whose MX records point at something that turns a
message into an HTTP request. Every general-purpose provider (SES receipt rules, Mailgun,
Postmark, SendGrid, Cloudflare Email Routing, ImprovMX) needs a domain the project owns.
For the diploma the project has no paid domain and no payment card on file, and the
deployment target is moving from AWS (ADR-0002) to Google Cloud, whose $300 trial covers
the defence period.

Google Cloud has one inbound mail path that needs no domain: App Engine's mail service,
one of the legacy bundled services still supported on the Python 3 runtime. Mail sent to
`anything@<project-id>.appspotmail.com` is delivered to the app as an HTTP POST to
`/_ah/mail/<address>`, with the raw message as the body.

## Decision

- **Production:** a minimal App Engine service receives `*@<project>.appspotmail.com` and
  relays each message, unchanged, to the backend's
  `POST /api/v1/webhooks/inbound-email`. The backend does not run on App Engine; the relay
  is the only thing that does.
- **The webhook contract is the relay's, not a vendor's:** the body is the raw RFC 5322
  message (`Content-Type: message/rfc822`); `X-Inbound-Recipient` carries the address it
  was sent to; `X-Inbound-Secret` carries a shared secret (`INBOUND_EMAIL_SECRET`).
  Without the secret the answer is 401; with no secret configured the endpoint is 404, so
  no deployment accepts mail by accident. MIME is parsed in the backend with the standard
  library (`app/domain/email_intake.py`), so changing the relay later changes nothing
  behind the webhook.
- **Addresses:** `receipts-<token>@<INBOUND_EMAIL_DOMAIN>`. Only the 64-bit random token is
  stored on the user; the domain is configuration, so moving where mail lands needs no
  migration. The user can replace the token, and the old address stops working at once.
- **Limits at the boundary:** messages over 10 MB are refused (413); at most 20 emailed
  receipts per user per UTC day; only PDF and image attachments are read, otherwise the
  HTML body reduced to text. A Message-ID already stored is not read again, so a relay
  that delivers twice makes one receipt.
- **Locally:** the `mail-relay` service in `docker-compose.yml` (`infra/dev/mail-relay/`)
  plays the App Engine relay: SMTP on `localhost:2525`, the same POST, the same headers.
  MailHog and Mailpit were considered and rejected — they capture mail for viewing and
  have no way to hand a message to a webhook.

## Consequences

- **Sender verification is weak and known to be.** The webhook compares From with the
  account email. From can be forged, and the relay has no DKIM result to pass on, so the
  address token is what actually keeps strangers out; the From check only stops a leaked
  address being used from another mailbox. Verifying DKIM in the backend (e.g. `dkimpy`)
  is the upgrade path if this ever leaves the diploma.
- **App Engine mail is a legacy service.** Google recommends third-party providers for new
  work. If it is withdrawn or does not work on the new project, the fallback is a provider
  webhook once a domain exists, or a shared Gmail inbox read over IMAP with plus-addresses
  (`inbox+<token>@gmail.com`) — both only replace the relay.
- **Emailed receipts skip the upload wizard.** No one is at a screen to confirm what was
  read, so they are stored at once; anything uncertain lands in review like a photo's.
  Telling an emailed copy from a photographed one is F11.5's job.
- **Content goes to the model.** The receipt's text or PDF is sent to the configured LLM,
  exactly as photos are (ADR-0006); PDFs use LiteLLM's provider-neutral `file` part, which
  a model that cannot read documents refuses, and the receipt then lands in review.
