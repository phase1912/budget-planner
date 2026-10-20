# ADR 0020: What personal data is processed, why, where and for how long

**Date:** 2026-10-17
**Status:** Accepted

## Context

Before the service is offered to the public (E17) and long before payments (E18), GDPR
asks the operator to know what personal data it processes, on what legal basis, where,
by whom and for how long (art. 5, 13, 30), and to let each user take and erase their
data (art. 15, 17, 20). F17.9 builds the rights; this record is what the privacy policy
(F17.9.4 drafts it, F17.7 finalises it) states, and what is checked when a feature adds
data. Wording to be reviewed in the E18 legal investigation.

## Decision: the record

### Data held, and why

| Data | Purpose | Legal basis (GDPR art. 6) | Kept |
|---|---|---|---|
| Account: name, email, password hash (Argon2id), language, currency, budget, forwarding token, when the email was confirmed, when and which terms were accepted | Signing in, letters about the account, showing figures | Contract, 6(1)(b) | Until the account is deleted |
| Receipts: merchant, date, lines, amounts, category, fiscal numbers, exchange rates; trips, per diem times, goals, advice, categories and rules, products, household membership | The service itself: reading receipts and budgeting | Contract, 6(1)(b) | Until the account is deleted |
| Income and balance (F23.10, F23.14): entries of money received (amount, date, kind, note), the usual income and payday, a starting balance and its date; the chosen palette and whether setup was done (F23.1, F23.9). A payslip or transfer document sent to be read (F23.11) is read in memory by the model and never stored — only the amount, date and payer the user confirms | Showing what is left and what the user has; the look they chose | Contract, 6(1)(b) | Until the account is deleted; never shared with a household |
| Conversations with the assistant (F21.1, ADR-0025): what the user wrote or said (as text — speech is turned into text by the browser's own recogniser, which in Chrome sends the sound to Google under the browser's terms; this service never receives sound), the assistant's answers and the cards it proposed, with whether each was saved | Answering the user and doing what they approved | Contract, 6(1)(b) | Until the user or the account deletes them; in the full export (F17.9) |
| Receipt photos and forwarded e-receipts (files) | Reading them; showing the receipt; a trip's settlement | Contract, 6(1)(b) | 90 days, then deleted by storage; the figures read from them stay (F17.9.3) |
| Export files | Giving the user their data or a settlement | Contract, 6(1)(b); art. 15/20 | 7 days |
| Messages through the contact form: reply address, topic, text (F17.10) | Answering the person who wrote | Legitimate interest, 6(1)(f); a data request, art. 12 | Not stored by the service: mailed to the support mailbox (F22.1.2) and a copy to the sender; kept there as long as the correspondence needs |
| Two-factor sign-in, when the user turns it on: the authenticator secret (encrypted) and hashes of unused recovery codes (F18.6.1, ADR-0021) | Protecting the account | Contract, 6(1)(b); security, art. 32 | Until turned off or the account is deleted |
| Plans granted to the account: plan, from, until, reason, who granted it, when taken back (F18.6.3) | Giving the plan; answering questions about it | Contract, 6(1)(b) | Until the account is deleted |
| The admin log: which admin did what to which account, when, with the reason (F18.6.3) | Accountability for admins' access to accounts | Legitimate interest, 6(1)(f) | Kept while the service runs; deleting an account removes its link to the entries |
| Sessions (refresh tokens) | Staying signed in | Contract, 6(1)(b) | 30 days unused, 90 at most (F17.8) |
| Kept in the visitor's browser (F17.7): the session tokens and account, chosen theme, language and list view, dismissed hints (localStorage), the app's own files (Cache Storage) | Signing in and keeping choices the user made | ePrivacy art. 5(3) exemption: strictly necessary or requested by the user — no consent asked; no cookies, nothing from other origins, kept so by `npm run lint:privacy` in CI | Until signing out or clearing the site's data |
| A letter to an admin on each sign-in of their account (F18.6.1) | Noticing a stranger's sign-in | Legitimate interest, 6(1)(f) | Not stored by the service |
| Activity of signed-in users: signing up, confirming the address, signing in, the first request of each day, uploading and storing a receipt, exporting — account and time only (F17.3.1) | Running and supporting the service, knowing whether it is used | Legitimate interest, 6(1)(f); never for advertising or profiling | 12 months, then deleted; with the account at once |
| Views of the public pages, counted per day, page and source (referring domain or campaign name) — no IP, no identifier, nothing on the device (F17.3.2) | Knowing whether the service has an audience | Not personal data once counted; nothing stored on the device, so no consent (ePrivacy) | Kept as counts |
| Client IP addresses (in memory, for rate limits) and request logs (URL, status, IP, user agent) | Security, abuse prevention, debugging | Legitimate interest, 6(1)(f) | Memory: minutes; Cloud Logging: 30 days (default bucket) |
| Database backups (disk snapshots) | Recovery from failure | Legitimate interest, 6(1)(f) | 7 days — a deleted account is gone from them within 7 days |

No special categories (art. 9) are asked for; a receipt may reveal some (a pharmacy
purchase), which the user chooses to upload. Nothing is sold, shared for advertising or
used to profile beyond the user's own budget advice. Analytics (F17.3) is cookieless and
aggregate; anything needing consent waits for F17.7's consent banner.

The controller is Bohdan Razhyk, a sole trader (JDG) in Poland, reached at
bohdan.razhyk.support@gmail.com or the Help page's form (F17.10, F22.1.2).

### Where, and by whom (processors)

All on Google, as the operator's processor under the Cloud Data Processing Addendum:

- **Google Cloud, `us-central1` (Iowa, USA):** Cloud Run (backend), the PostgreSQL
  virtual machine and its snapshots, Cloud Storage (photos, exports), Secret Manager,
  Cloud Logging, App Engine (mail in and out, ADR-0013, ADR-0019).
- **Vertex AI Gemini, `us-central1`:** reads receipt photos and names, and answers the assistant's conversations (F21.1); under Google
  Cloud's terms, customer data is not used to train models.
- **Firebase Hosting:** serves the web app's static files from Google's global CDN;
  it holds no user data beyond request logs.

### Transfer outside the EEA

Data is stored and processed in the USA. Google LLC is certified under the EU-US Data
Privacy Framework, and the Cloud DPA includes the Standard Contractual Clauses as a
fallback (art. 45, 46).

### The user's rights, as built

- Access and portability (art. 15, 20): Profile → "Download everything" — a ZIP of all
  rows held about the user as JSON, with the photos still kept (F17.9.2).
- Erasure (art. 17): Profile → "Delete account", with the password — every row by
  cascade, the files by prefix, the household handed on (F17.9.1).
- Rectification (art. 16): every receipt, line and profile field is editable.
- Withdrawing from letters: only account letters are sent (confirmation, reset, address
  change); there is no newsletter to unsubscribe from.

## Consequences

- A feature that adds personal data, a processor or a retention period updates this
  record and the privacy pages in the same change.
- Moving off Google, or adding a mail provider when a domain is bought (E19), adds a
  processor here and to the privacy policy.
