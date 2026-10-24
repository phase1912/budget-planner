# Delivery backlog

> Generated from [`backlog.yaml`](backlog.yaml) by `scripts/backlog_sync.py render`.
> Edit the YAML, not this file.

27 epics · 203 features · 415 tasks written so far.

23 epics are in the diploma project's scope; 4 are planned but out of it.

| Epic | Title | BRD | Features | Groomed | Phase | Scope |
|---|---|---|---|---|---|---|
| E0 | Foundation & Delivery Platform | — | 11 | yes | 1 | Diploma |
| E1 | Identity & Account | BR-7, N2 | 5 | yes | 1 | Diploma |
| E2 | Receipt Ingestion & Storage | BR-1 | 5 | yes | 1 | Diploma |
| E3 | Receipt Parsing & Extraction | BR-1 | 8 | no | 1 | Diploma |
| E4 | Multi-Photo Position Matching | BR-2 | 8 | yes | 1 | Diploma |
| E5 | Spend Categorization | BR-3 | 8 | no | 1 | Diploma |
| E6 | Monthly Budget Calculation | BR-4 | 7 | no | 1 | Diploma |
| E7 | Statistics, Comparison & Export | BR-5 | 6 | no | 1 | Diploma |
| E8 | Goals & AI Optimization Advice | BR-6 | 10 | yes | 1 | Diploma |
| E9 | Web Client Foundation | — | 8 | yes | 1 | Diploma |
| E10 | Security, Privacy & Observability | N1, N2, N3, N5 | 6 | no | 1 | Out of scope |
| E11 | Alternative Receipt Intake | — | 6 | yes | 2 | Diploma |
| E12 | Household & Shared Budgets | — | 10 | yes | 2 | Diploma |
| E13 | Aggregated Purchase Analytics | — | 8 | yes | 2 | Diploma |
| E14 | B2B Export & Accounting Integrations | — | 8 | no | 2 | Out of scope |
| E15 | Receipt Accuracy & Trust | — | 6 | yes | 2 | Diploma |
| E16 | Personal Price History | — | 4 | yes | 2 | Diploma |
| E17 | Landing, Search and Analytics | — | 11 | yes | 2 | Diploma |
| E18 | Subscriptions and Payments | — | 6 | yes | 2 | Out of scope |
| E19 | Advertising | — | 4 | yes | 2 | Diploma |
| E20 | Trips | — | 5 | yes | 2 | Diploma |
| E21 | Voice and Chat Assistant | — | 17 | yes | 2 | Diploma |
| E22 | Android App | — | 5 | yes | 2 | Diploma |
| E23 | Improvements | — | 23 | no | 2 | Diploma |
| E25 | iOS App | — | 3 | yes | 2 | Diploma |
| E26 | Native Apps | — | 2 | no | 3 | Out of scope |
| E24 | Bugfixes | — | 3 | no | 2 | Diploma |

---

## E0 — Foundation & Delivery Platform

**BRD sections:** — · **Phase:** 1 · **Scope:** Diploma

Everything required before a single business requirement can be implemented: repository layout, both runtimes, the database and migration baseline, the local development environment, CI, and a BDD harness that executes the BRD's Gherkin scenarios directly.

### F0.1 — Repository layout and language tooling

*Requirements: —*

A contributor can clone the repository and get a lint-clean, type-checked workspace for both the Python and the TypeScript side with one documented command.

- **F0.1.1** Establish the repository layout (backend, frontend, infra, docs, scripts) — Create the top-level directories with placeholder READMEs describing what belongs in each. Document the boundary rule: no import may cross from frontend to backend except through the generated OpenAPI client.
- **F0.1.2** Set up the Python project with uv and pyproject.toml — Python 3.12, uv-managed lockfile, dependency groups for runtime vs dev. Pin FastAPI, SQLAlchemy 2.x, Alembic, pydantic-settings, anthropic.
- **F0.1.3** Configure ruff, mypy and pre-commit for the backend — ruff for lint and format, mypy in strict mode for app code. pre-commit runs both plus trailing-whitespace and end-of-file fixers. CI must run the same versions.
- **F0.1.4** Add EditorConfig, license and contribution conventions — .editorconfig covering both languages, LICENSE, and a CONTRIBUTING.md that states the branch naming and commit message conventions used by the ticket workflow.
- **F0.1.5** Support feature-scoped branches and pull requests in the ticket workflow — The ticket-first workflow (working-agreement.md, the task skill, AGENTS.md) only covered one task per branch per pull request. Tasks inside one feature routinely overlap in practice, producing diffs that conflicted across separate branches. Add a feature-scoped mode: when the unit of work is a whole feature rather than one task, use a single feature/<key>-<slug> branch, implement every task under the feature as one consistent pass instead of task-by-task in isolation, and open one pull request whose body closes every task issue under the feature (one `Closes #N` per issue). The single-task workflow is unchanged.

### F0.2 — FastAPI application skeleton

*Requirements: —*

A running API process exists with configuration, health reporting, a uniform error envelope and a published OpenAPI schema, so feature work only adds routers.

- **F0.2.1** Application factory and router registration — create_app() assembling middleware, exception handlers and routers. Routers are registered from a single module so feature epics add one line, not wiring.
- **F0.2.2** Configuration module using pydantic-settings — Typed settings with env-var layering and fail-fast validation on boot. No direct os.environ reads anywhere else in the codebase.
- **F0.2.3** Health and version endpoints — GET /health returning liveness plus database reachability, and GET /version returning build SHA and parser version (the latter is required by BRD A15).
- **F0.2.4** Uniform error envelope and global exception handlers — RFC 7807 problem+json responses. Validation, not-found, permission and internal errors each map to a stable machine-readable code that the client can branch on. BRD A2 and B6 both require reasons to be returned, not just status codes.

### F0.3 — PostgreSQL, SQLAlchemy and Alembic baseline

*Requirements: —*

The persistence layer is established with async sessions, migration tooling and model conventions, so entities from the BRD data model can be added incrementally.

- **F0.3.1** Async SQLAlchemy engine and request-scoped session dependency — Async engine with a pool sized from settings, and a FastAPI dependency yielding a session per request with commit-on-success and rollback-on-exception semantics.
- **F0.3.2** Initialise Alembic with the async migration template — Alembic configured against the same settings object, autogenerate enabled, and a documented policy that every schema change ships as a reviewed migration.
- **F0.3.3** Declarative base and model conventions — UUID primary keys, created_at/updated_at on every table, and an explicit constraint naming convention so autogenerated migrations are deterministic.
- **F0.3.4** Baseline migration enabling required PostgreSQL extensions — Enable pgcrypto (needed for encryption at rest under BRD N1) and any UUID support the chosen generation strategy requires.

### F0.4 — Local development environment

*Requirements: —*

A developer can bring up the full stack — API, client, PostgreSQL and S3-compatible object storage — locally with one command.

- **F0.4.1** Docker Compose stack with PostgreSQL and MinIO — Compose file with pinned images, named volumes, health checks, and a bootstrap step creating the receipts bucket. MinIO stands in for production object storage. Lives at the repository root, not under infra/, so `docker compose up` works from a fresh clone with no extra flags.
- **F0.4.2** Task runner targets for the common workflows — up, down, migrate, test, lint, typecheck. Both languages behind the same interface so nobody memorises two toolchains. The `seed` target landed with the seed script itself in F5.8.
- **F0.4.4** Quickstart section in the README — Clone-to-running instructions, prerequisites with versions, and how to obtain and configure the Claude API key.

### F0.5 — Continuous integration

*Requirements: —*

Every pull request is automatically linted, type-checked and tested on both sides, and schema drift is caught before merge.

- **F0.5.1** Backend CI workflow — GitHub Actions job running ruff, mypy and pytest against a service-container PostgreSQL, with dependency caching keyed on the uv lockfile.
- **F0.5.2** Frontend CI workflow — ESLint, tsc --noEmit, Vitest and a production build, so type or build breakage cannot reach the default branch.
- **F0.5.3** Migration drift check — CI job asserting that alembic autogenerate against the models produces an empty diff, catching model changes that shipped without a migration.
- **F0.5.4** Pull request template and CODEOWNERS — PR template linking back to the closing issue and listing the BRD requirement IDs the change satisfies, so traceability from BRD to commit is mechanical.

### F0.6 — BDD acceptance harness

*Requirements: —*

The Gherkin scenarios already written in the BRD execute as the automated acceptance suite, so acceptance criteria and regression tests are the same artefact.

- **F0.6.1** pytest foundation with async support and isolated test database — pytest-asyncio, a per-run test database created from migrations, and transactional rollback between tests for isolation.
- **F0.6.2** Extract the BRD Gherkin into executable .feature files — Move the scenarios from BRD sections BR-1 through BR-6 into tests/features/, one file per business requirement, preserving the wording verbatim so the documents stay comparable. Steps are stubbed as skipped until their epic is implemented.
- **F0.6.3** Test data factory infrastructure and conventions — The factory library, the base class and the naming convention that lets a scenario read as business language rather than ORM setup. Delivers no per-entity factory: no domain entity exists yet at E0, and each is added by the epic that introduces it — the same rule F1.3's cross-user suite follows.
- **F0.6.4** Coverage reporting and BRD traceability report — Coverage gate in CI, plus a generated report mapping each BRD requirement ID (A1-A15, B1-B9, C1-C7, D1-D7, E1-E6, F1-F9, N1-N6) to the tests covering it.

### F0.7 — Configuration, secrets and environments

*Requirements: —*

Configuration and secrets are handled consistently across local, CI and deployed environments, with no credential ever committed.

- **F0.7.1** Document the settings surface and provide .env.example — Every setting listed with purpose, default and whether it is required, including the thresholds BRD section 10 defers to design time.
- **F0.7.2** Secret handling for CI and deployment — GitHub Actions secrets for the Claude API key and database credentials, with a documented rotation procedure and secret scanning enabled on the repository.
- **F0.7.3** Environment matrix definition — Define local, staging and production: what differs, which is authoritative for data, and which AI model tier each uses.

### F0.8 — Global architecture and domain model documentation

*Requirements: —*

A written reference for the system's shape and its business rules, kept current as the codebase grows, so a reader (human or agent) can act on global context instead of re-deriving it from the BRD or from reading the whole codebase.

- **F0.8.1** Write docs/architecture/overview.md and domain-model.md — overview.md: component boundaries, layering (router/service/repository/port), the ingestion pipeline's three requirement-driven properties (async processing, manual_review as a state, same-receipt-only matching), security posture, and explicit non-goals from BRD section 4.2. domain-model.md: entities, the receipt lifecycle, and a numbered list of invariants traced to BRD requirement IDs, plus a table of the BRD's open questions and which epics they block. Both documents carry an explicit instruction to be updated in the same commit as any change that invalidates them, and CLAUDE.md and the task skill reference them as required reading before structural or business-rule changes.

### F0.9 — Cloud deployment on Google Cloud, deployed on every merge

*Requirements: —* · *Blocked by: F0.5, F0.7*

The application runs in the cloud from infrastructure-as-code, not by hand, and every merge to main deploys itself. Targets Google Cloud (ADR-0014, which replaces the AWS decision in ADR-0002) at the smallest sizes that run it reliably: one production environment, a scale-to-zero backend, Postgres on a free-tier VM, and free static hosting, about $1-4 a month. Staging is deliberately absent while the author is the only user.

**Demonstrated by:** No screen of its own: merge a visible change to main, watch the Deploy workflow go green, and open the production URL on a phone to see it live — sign in, upload a receipt photo and find it read, and forward an e-receipt to the appspotmail address shown in Profile.

- **F0.9.1** Decide the Google Cloud deployment — ADR-0014: Cloud Run for the backend, Postgres on an e2-micro VM, Cloud Storage as the backend's service account (no keys), Firebase Hosting, Vertex AI Gemini, App Engine for inbound mail, Secret Manager, Workload Identity Federation for CI. Records costs, limits and risks; marks ADR-0002 superseded; updates environments.md, secrets.md and configuration.md.
- **F0.9.2** Production backend image and cloud settings — A production Dockerfile (no reload, non-root, listens on $PORT); the Anthropic key stops being required now that every model goes through the llm_* settings (ADR-0006); Vertex AI project and location become settings passed to the agent; a Cloud Storage adapter behind StoragePort reaches the photo bucket keylessly, since the organisation forbids service account keys.
- **F0.9.3** Terraform for the production environment — One root module under infra/terraform with state in GCS: APIs, network, the database VM with its data disk and daily snapshots, the photo bucket, Artifact Registry, secrets, the Cloud Run service and migrations job, App Engine, service accounts with least privilege, GitHub Workload Identity Federation and a billing budget with alerts.
- **F0.9.4** Inbound mail relay on App Engine — The production counterpart of infra/dev/mail-relay: receives *@<project>.appspotmail.com and posts each raw message to the intake webhook with the shared secret (ADR-0013).
- **F0.9.5** Deploy on every merge to main — A Deploy workflow that runs after CI passes on main: build and push the backend image, run migrations as a Cloud Run job, deploy the service, build and publish the frontend to Firebase Hosting, redeploy the mail relay when it changed, and smoke-test the health endpoint. Terraform gets fmt and validate checks in CI.
- **F0.9.6** First deployment and its runbook — Apply the infrastructure, run the first deploy, check the demo end to end (including presigned photo URLs signed through IAM) and write the runbook: bootstrap, apply, restoring the database from a snapshot, and stopping costs.

### F0.10 — Identity, access and NFR acceptance criteria in the BRD

*Requirements: —*

Every existing BRD scenario opens with "Given the user is logged in", but the BRD itself never says what that means, and section 8's non-functional requirements (N1-N6) have EARS text with no Gherkin at all — both are real gaps F0.6.2's extraction correctly left untouched, since it could only move what the BRD already had. This closes them the same way BR-1..BR-6 were written: business-approved acceptance criteria first, so E1 (Identity & Account) and E10 (Security, Privacy & Observability) have something to build against instead of inventing it mid-epic.

- **F0.10.1** BR-7 Identity & Access, and NFR acceptance scenarios — Adds a new BR-7 section to the BRD (EARS requirements + Gherkin) covering registration, login, logout and session refresh; an admin role limited to service operation (no exception to N2 — an admin never reads another user's receipts or statistics); and sign-in via Google/Facebook OIDC coexisting with password auth, linked to an existing account only on a verified email match, with an explicit scenario rejecting a link attempt on an unverified email (the standard account-takeover vector for social login). Adds a Gherkin block to BRD section 8 for N1-N6, which today are EARS-only. Extends BRD section 9's data model with the User.role field and the identity-provider link entity BR-7 needs. Mirrors F0.6.2's own job for this new material: the scenarios land in tests/features/br7_identity_and_access/ and tests/features/nfr_cross_cutting/, wired via pytest-bdd and skipped pending E1/E10, and scripts/generate_brd_traceability.py regenerates brd-traceability.md to include them. Updates E1's `br:` list in backlog.yaml to add BR-7 alongside N2.

### F0.11 — The product's flows tested end to end in a browser

*Requirements: —*

Testers kept finding what a machine could have: a step that threw a typed income away, an English refusal on a Ukrainian screen, a receipt stored where nobody looks. A suite drives a real browser through the product's main flows against the local stack — signing up, onboarding, adding receipts, expenses and incomes, the AI's consent, the family, the assistant, settings — at phone, tablet and desktop widths, keeping screenshots to look at. Receipt reading, the weakest and most varied part, gets a corpus of cases (receipts, transfers, incomes; by country, Europe first) in one format, so a new case is a new folder, not new code: run deterministically through a stand-in reader everywhere, and through the real model on demand. Run by one command, by the owner or by the coding agent, and in CI on every pull request.

**Demonstrated by:** Run the suite: every flow passes at 375, 768 and 1280 px and leaves its screenshots; add a folder with a Polish receipt and its expected.json, run again, and the new case is checked through upload, review and storing.

- **F0.11.1** The suite's frame — pytest with Playwright (Chromium and WebKit) under backend/tests/e2e, marked so the unit run skips it, against the docker compose stack; test data made by the existing factories straight in the database; the confirmation and reset links taken from the local mail log; every flow parametrised over 375, 768 and 1280 px, saving screenshots, and traces on failure. One command runs it; the working agreement and CLAUDE.md say how.
- **F0.11.2** A stand-in reader for tests — A reading engine chosen by configuration that answers a known file with its case's expected result, and a scripted model for the assistant, behind the existing ports (LSP: the same contract and errors as the real adapters). It is refused outside local and test environments, with a test that production can never select it.
- **F0.11.3** The receipts corpus — One case format for the browser suite and scripts/evaluate_reading.py: a folder of photos or PDFs and an expected.json saying what they are — receipts (several per photo or one in parts), money sent, money received — with merchant, date, currency, total and lines. Folders by country. Synthetic cases with invented shops are committed and run everywhere; real people's receipts stay in the ignored private folder, run with the real model on demand, with a score per country. A README on adding a case.
- **F0.11.4** The main flows, first wave — Sign-up and confirming the address; onboarding, including Next with a typed income; a receipt uploaded, reviewed, stored and found in its month; a manual expense; an income making a card and its balance; the AI's consent refused and allowed; a family with a second member; the assistant proposing a card that is approved; settings, language and deleting the account. Each in Ukrainian at least once, checking no English reaches the screen.
- **F0.11.5** In CI — A workflow job brings up the stack, runs the suite on every pull request and keeps the screenshots and traces of a failed run as artifacts; the run fits in about ten minutes.

---

## E1 — Identity & Account

**BRD sections:** BR-7, N2 · **Phase:** 1 · **Scope:** Diploma

Every BRD scenario begins with "Given the user is logged in", and N2 forbids one user's data from reaching another. This epic establishes authentication, session handling, the user profile fields from the BRD data model, and the scoping guarantee that all later epics depend on. Full stack, and paired feature by feature rather than layer by layer: the login and registration screens ship inside F1.1 with the endpoints they post to, and token storage, transparent refresh and the protected route table ship inside F1.2 with the session model they depend on. E9 owns only the frontend groundwork that has no domain dependency.

### F1.1 — Registration and login

*Requirements: —* · *Blocked by: F9.4, F9.6*

A person can create an account with an email and password and authenticate with it, through the product rather than through curl: the screens ship with the endpoints.

**Demonstrated by:** Create an account on /register, sign out, sign back in on /login, and land on the root route as yourself. Then fail a sign-in and confirm a wrong password and an unknown address are indistinguishable (BRD N2).

- **F1.1.1** User table migration and SQLAlchemy model — Implements the User entity from BRD section 9: user_id, email, password_hash, currency, budget_limit. The goal relationship is added by epic E8; currency and budget_limit land here because they are account-level settings.
- **F1.1.2** Password hashing and strength policy — Argon2id with documented parameters, a minimum-length policy, and a check against a common-password list. Hashing cost must be configurable per environment so tests stay fast without weakening production.
- **F1.1.3** POST /auth/register endpoint — Validates the payload, rejects duplicate emails without revealing whether an address is registered, and returns the created account with a session.
- **F1.1.4** POST /auth/login endpoint — Constant-time credential verification, a uniform error for both unknown email and wrong password, and throttling on repeated failures.
- **F1.1.5** Acceptance tests for registration and login — Covers the happy path, duplicate registration, wrong password, and the guarantee that responses do not leak account existence.
- **F1.1.6** Login and registration screens — The two public routes, built from docs/design/screens/login.html and register.html and posting through the generated client. The sign-in failure shows one message for both an unknown address and a wrong password, matching what F1.1.4 returns — the screen must not leak what the endpoint withholds.
- **F1.1.7** Post-login landing at the root route — Where signing in actually lands, per docs/design/screens/home.html: account facts, an honest "no receipts yet" and one way forward. F6.7 later replaces the body of this same route with the dashboard rather than adding a second one (ADR 0004).

### F1.2 — Session and token management

*Requirements: —* · *Blocked by: F9.4*

An authenticated session persists across requests, can be refreshed, and can be revoked on logout — including on the client, where the token is held and where expiry decides what the user sees.

**Demonstrated by:** Stay signed in across a reload; let the access token expire mid-edit and watch the action complete anyway; sign out on one device and find the other rejected.

- **F1.2.1** Access token issuance — Short-lived JWT carrying the user id and issued-at, signed with a key from settings. Claims kept minimal — no financial data in the token.
- **F1.2.2** Refresh token storage and rotation — Server-side refresh tokens with rotation on use and reuse detection that revokes the whole family, so a stolen refresh token cannot be replayed.
- **F1.2.3** Refresh and logout endpoints — POST /auth/refresh exchanging a valid refresh token, POST /auth/logout revoking the current session.
- **F1.2.4** Current-user dependency — A FastAPI dependency resolving the authenticated user, returning 401 with the standard error envelope when absent or expired. This is the single entry point every protected route uses.
- **F1.2.5** Token storage and the authenticated fetch layer — Where the access token lives on the client and how the refresh in F1.2.2 is spent: a 401 triggers one refresh and replays the original request, so a token expiring mid-edit does not cost the user their work. Concurrent 401s share a single refresh rather than racing to rotate the family.
- **F1.2.6** Protected route table and expiry redirect — The public-versus-authenticated split F9.4.3 left open, the guard in front of it, and the redirect when a session ends — returning the user to where they were once they sign back in, not to the root.

### F1.3 — Per-user data scoping guarantee

*Requirements: —*

Satisfies BRD N2 structurally rather than by convention: it must be difficult to write a query that returns another user's data.

**Demonstrated by:** No screen of its own — it is what every other feature's cross-account check rests on. Proven by signing in as a second account and finding the first account's receipts, statistics and goals absent, with direct URLs answering 404 rather than 403.

- **F1.3.1** Request-scoped user context — The authenticated user id is available to the persistence layer for the duration of the request without being threaded manually through every function signature.
- **F1.3.2** Ownership-enforcing repository base class — A base repository that applies the user_id filter automatically for all user-owned entities. Bypassing it requires an explicit, greppable escape hatch.
- **F1.3.3** Cross-user access test suite — For every user-owned resource, assert that user B receives 404 rather than 403 for user A's records, so existence is not disclosed. This suite is extended by each later epic that introduces a new owned entity.

### F1.4 — User profile and preferences

*Requirements: —* · *Blocked by: F1.1, F9.4*

A user can set the account currency and an optional monthly budget limit, which BRD D7 uses to express spend as a percentage of target.

**Demonstrated by:** Set a monthly limit in Preferences and see it reflected on the root route. Try to change currency once receipts exist and find the control locked with the reason.

- **F1.4.1** GET and PATCH /me endpoints — Read and partially update the profile. Changing budget_limit must not retroactively rewrite finalised monthly snapshots — it affects presentation only.
- **F1.4.2** Currency validation and the single-currency assumption — ISO 4217 validation, and an explicit guard rejecting a currency change once receipts exist, since BRD section 4.2 puts conversion out of scope.
- **F1.4.3** Profile screen — Displays and edits currency and monthly budget limit, backed by a MobX store following the conventions set in epic E9.

### F1.6 — Signing in with Google and Apple

*Requirements: N2* · *Blocked by: F1.2, F22.2*

A password and a confirmation letter are the slowest way into the service on a phone. Google and Apple sign the user in through OpenID Connect: the server checks the provider's ID token (issuer, audience, signature from its published keys, nonce, expiry) and signs in, or creates, the account of that verified address; an existing account with the same address links the provider after signing in once with its password, never silently. Wherever Google is offered in the iOS app, Apple is offered too (App Review 4.8). Built for whichever store goes first (E22 or E25), on the web as well.

**Demonstrated by:** On a phone, tap "Continue with Google", pick the account and land on Home with no password and no letter; in Settings see Google linked, add a password, unlink it.

- **F1.6.1** OpenID Connect sign-in on the server — POST /api/v1/auth/oidc/{provider} taking an ID token (and the nonce it was asked with) for Google or Apple, verified against the provider's keys and our client ids; a linked-identities table (provider, subject, user) by add-only migration; a new account from a verified address, confirmed by the provider; an address that already has an account asks for its password before linking; Apple's private relay addresses kept as given. The same tokens and refresh as a password sign-in; an ADR for providers, linking and what is stored. Tests with a stubbed key set, including a forged token, a wrong audience and another user's subject (N2).
- **F1.6.2** The buttons, on the web and in the apps — "Continue with Google" and "Continue with Apple" on sign-in and sign-up, following each provider's button rules; on the web through their JavaScript sign-in, in the apps through the native sign-in (Credential Manager on Android, AuthenticationServices on iOS) behind the platform module; Settings lists linked providers, links and unlinks one while a password or another provider remains. Three languages; checked at 375, 768 and 1280 px.
- **F1.6.3** Apple's rules for its sign-in — Deleting an account revokes its Apple tokens through Apple's REST API (App Review 5.1.1), the server-to-server notifications for consent revoked or an email changed are handled, and the client secret is a signed JWT from a key in Secret Manager, rotated before it expires; Terraform and the deployment documentation updated.

---

## E2 — Receipt Ingestion & Storage

**BRD sections:** BR-1 · **Phase:** 1 · **Scope:** Diploma

Accepting receipt photos: format validation, the two upload modes with their photo-count and size limits, durable encrypted storage of the originals, and asynchronous processing status. Covers BRD A1 through A8 and the storage half of A12. The upload screen is built here rather than parked in a trailing interface feature: F2.1 puts it on screen, and F2.2, F2.3 and F2.5 each extend it as they land, so every feature in this epic can be exercised by using the product.

### F2.1 — Upload endpoint, format validation and the upload screen

*Requirements: A1, A2* · *Blocked by: F1.2, F9.4*

Submitted files are validated as JPEG, PNG, HEIC or PDF-scan by content inspection rather than by extension, and rejections state the accepted formats — with the screen that submits them. The first slice of docs/design/screens/upload-1-photos.html: pick files, send them, see what came back.

**Demonstrated by:** Choose a photo on /upload and send it. Then choose a .docx and watch it be refused with the accepted formats named, per the "Unsupported file" panel in docs/design/screens/states.html.

### F2.2 — Single-receipt upload mode

*Requirements: A3, A4, A7, A8* · *Blocked by: F2.1*

One receipt captured across up to 10 photos totalling at most 50 MB, with limit violations rejected and explained. Adds the mode selector, the photo strip and the count-and-size meter to F2.1's screen — the limits are enforced on the server and shown before bytes are sent, not only after.

**Demonstrated by:** Add photos in single-receipt mode and watch the meter fill; add an eleventh and see the 10-photo limit refuse it in words rather than silence.

- **F2.2.1** Extend upload endpoint for multiple files and limits — Modify POST /receipts/upload to accept a list of files. Enforce a maximum of 10 files per request and a total payload size of 50 MB. Return a 400 with a specific RFC 7807 problem json when limits are exceeded (BRD A4, A8).
- **F2.2.2** Upload screen mode selector and photo strip — Update the upload UI to include a mode selector (Single vs Multiple) and a photo strip for previewing selected files, plus a meter showing count/size against the 10-photo/50MB limits before submission.
- **F2.2.3** BDD scenarios for single-receipt mode limits — Write and wire acceptance tests verifying the 10-photo and 50MB limits are enforced on the server and explained clearly on rejection.

### F2.3 — Multiple-receipts upload mode

*Requirements: A3, A5, A6, A7, A8* · *Blocked by: F2.2*

Several distinct receipts in one session, one upload line each, with the 10-photo and 50 MB limits applied independently per line so one bad line cannot fail the others. Adds the second mode and the per-line UI to the same screen.

**Demonstrated by:** Add two upload lines, overload the first past 10 photos, and confirm the second line is untouched and still submits — the independence A7 requires, visible rather than asserted.

- **F2.3.1** Multi-line multiple-receipts upload endpoint — Extend the API to accept multiple distinct receipts in one request, with limits (10 photos / 50MB) applied independently to each receipt (BRD A7).
- **F2.3.2** Multiple-receipts mode frontend — Add the multi-line UI for multiple-receipts mode. Let the user add distinct upload lines, each tracked and validated independently.

### F2.4 — Encrypted object storage for receipt images

*Requirements: A12, N1* · *Blocked by: F2.1*

Original images are stored in object storage encrypted at rest, referenced from the receipt record, and retrievable only by their owner via time-limited URLs.

**Demonstrated by:** No screen of its own — the photo thumbnails on F2.1's screen render through the time-limited URL, so they prove the path works. Ownership is shown by signing in as a second account and getting a 404 for the first account's image URL (BRD N2).

- **F2.4.1** S3-compatible storage integration — Implement a storage service client (e.g., using aiobotocore or minio) that uploads files to the configured bucket with encryption at rest (BRD A12, N1).
- **F2.4.2** Time-limited URL generation — Implement an endpoint or service to generate presigned, time-limited URLs for viewing receipt images, ensuring only the owner can access them.

### F2.5 — Asynchronous ingestion pipeline and status tracking

*Requirements: N4* · *Blocked by: F2.1*

Upload returns immediately with a tracking handle while parsing proceeds in the background, so the 10-second target of N4 is a processing budget rather than a request timeout. Adds the processing state to the upload screen.

**Demonstrated by:** Send a batch and watch the "Reading 2 receipts" state from docs/design/screens/states.html — then leave the page and come back to find the work still progressing.

- **F2.5.1** Background worker queue and task submission — Introduce a background task queue (e.g. using FastAPI BackgroundTasks or celery/rq) to process receipts asynchronously and return a tracking handle immediately (BRD N4).
- **F2.5.2** Processing state API and frontend polling — Add an endpoint to query the status of a given tracking handle. Update the upload wizard to poll this endpoint and render the processing state panel.

---

## E3 — Receipt Parsing & Extraction

**BRD sections:** BR-1 · **Phase:** 1 · **Scope:** Diploma

Turning a validated photo into a structured receipt: field extraction, confidence handling, manual-review flagging, duplicate detection and persistence with provenance. Covers BRD A9 through A15. This is where photographing a receipt starts paying off, so F3.1 puts step 2 of the upload wizard on screen and every later feature in the epic extends it. Nothing here ships as extraction that only a test can see.

### F3.1 — Vision extraction, and seeing what was read

*Requirements: A9* · *Blocked by: F2.1, F9.4*

A versioned, testable adapter over the Claude vision API that turns receipt images into structured output, with the prompt and schema under source control — and the screen that shows the result. Introduces the three-step wizard frame, because this is the first point at which a second step exists to step to (the frame was formerly F2.6's). First slice of docs/design/screens/upload-2-extracted.html.

**Demonstrated by:** Photograph a real receipt, send it, and read the merchant, date and line items back off step 2 of the wizard.

### F3.2 — Extraction schema and validation

*Requirements: A9* · *Blocked by: F3.1*

Merchant, transaction date, transaction time, line items (name, quantity, unit price, total price) and total amount, validated for internal arithmetic consistency. The screen gains the per-receipt footer reconciling the sum of lines against the printed total.

**Demonstrated by:** Upload a receipt whose lines do not add up to its printed total and see the disagreement stated on step 2 rather than absorbed silently.

### F3.3 — Confidence scoring and low-confidence flagging

*Requirements: A10* · *Blocked by: F3.2*

Per-field confidence recorded, and fields below threshold marked "low confidence" and surfaced for confirmation instead of being silently accepted. The screen marks those fields where they appear.

**Demonstrated by:** Upload a blurred receipt and find the unreadable total marked "low confidence" on step 2 instead of presented as fact.

### F3.4 — Manual-review status for missing critical fields

*Requirements: A11* · *Blocked by: F3.3*

A receipt without an extractable total or date is marked "requires manual review" and excluded from all automated budget calculation until a human resolves it — and says so on its face wherever it appears.

**Demonstrated by:** Upload a receipt with its total torn off; the screen says the total could not be read and that the receipt is held out until it is supplied, per the "Held out of the total" panel in docs/design/screens/states.html.

### F3.5 — Receipt persistence with provenance

*Requirements: A12, A13, A15* · *Blocked by: F3.2*

Header, line items and image reference stored under a unique receipt id, owned by the submitting account, stamped with processing time and parser version.

**Demonstrated by:** No screen of its own — it is proven by what depends on it. Complete the wizard, then re-upload the same receipt and watch F3.6 recognise it, which is only possible if the first one was really stored. F3.8 then shows it in a list.

### F3.6 — Duplicate receipt detection

*Requirements: A14* · *Blocked by: F3.5*

A receipt matching an existing one on merchant, date and total prompts the user to confirm before storing, rather than being silently accepted or silently dropped. Two trips to one shop on one day are normal, so this asks rather than decides.

**Demonstrated by:** Upload the same receipt twice and answer the prompt both ways — once skipping, once storing it as new — per the "Possible duplicate upload" panel in docs/design/screens/states.html.

### F3.8 — Receipt list and detail

*Requirements: A12, A13, N2* · *Blocked by: F3.5, F1.2, F9.4*

What "Receipts" in the navigation means: the endpoint listing an account's stored receipts newest first with pagination, and the screens over it — the list, and a detail dialog showing the merchant and everything bought. Screens at docs/design/screens/receipts.html and receipt-detail.html. Deliberately no per-category summary in the dialog yet.

**Demonstrated by:** Open Receipts, page through them, and click one to read its line items. Sign in as a second account and confirm the first account's receipts are absent and its receipt URL returns 404 rather than 403 (BRD N2).

### F3.9 — Correct a stored receipt

*Requirements: A11, D6* · *Blocked by: F3.8*

Edit the merchant, date, total and line items of a receipt that is already stored, from the detail dialog the "Edit" button already sits in. A11 marks a receipt "requires manual review ... until resolved" and D6 assumes a receipt can be edited after the fact, but nothing in the product can currently change a stored receipt: there is no PATCH endpoint and the button has no handler. Groomed late because F6.5 was written assuming this capability rather than building it.

**Demonstrated by:** Open a stored receipt whose total the parser misread, correct it from the detail dialog, and see the list row and the receipt itself both show the new figure.

---

## E4 — Multi-Photo Position Matching

**BRD sections:** BR-2 · **Phase:** 1 · **Scope:** Diploma

Recognising that a line item appearing on two overlapping photos of one long receipt is the same purchase, so it is counted once — while never collapsing genuinely repeated purchases made on different receipts. Covers BRD B1 through B9.

### F4.1 — Independent per-photo extraction for comparison

*Requirements: B1* · *Blocked by: F3.1*

Each photo is parsed on its own before any comparison, so a match decision is never an artefact of parsing the two images together. Step 2 of the wizard gains the per-photo provenance that makes this visible: which frame each line came from.

**Demonstrated by:** Photograph one long receipt in two overlapping frames and see, on step 2, each item attributed to the frame it was read from.

- **F4.1.1** Parse photos independently in _run_extraction — Modify process_upload_job_task to parse each image sequentially/independently rather than in one batch array to Claude. Add file_id tracking per line item.
- **F4.1.2** Expose per-photo provenance in frontend Step 2 — Update frontend receipt wizard step 2 to show which frame each line item came from (tagging line items with their source image).

### F4.2 — Position comparison rules

*Requirements: B2, B3, B4* · *Blocked by: F4.1*

Item name, unit price, quantity and total price must all match exactly for a pair to be "same position"; any difference makes it "different position". Ships with the conflict card that shows the comparison field by field, so the verdict is legible rather than asserted.

**Demonstrated by:** Upload the overlapping pair and read the evidence table for a matched item — all four fields ticked — and for a near-match where one price differs.

- **F4.2.1** Implement position comparison logic — Compare extracted items on exact match of name, unit price, quantity, and total. Yield matches or mismatches.
- **F4.2.2** Build conflict card UI — Show the conflict card field by field comparison as specified in design.

### F4.3 — Same-receipt scoping guard

*Requirements: B5, B9* · *Blocked by: F4.2*

Comparison runs only between photos of one physical receipt. Identical items on two distinct transactions are two purchases, never a duplicate — this is the requirement most likely to be violated by a naive deduplication implementation.

**Demonstrated by:** Upload two separate receipts a week apart that each contain "Milk 2% 1L" at 4.50 and confirm both purchases survive, with no match offered between them.

- **F4.3.1** Restrict position match to single receipt — Ensure the comparison only runs across photos that belong to the same physical receipt group, and never across separate receipts.

### F4.4 — Comparison failure handling

*Requirements: B6* · *Blocked by: F4.2*

If either photo failed to parse, return "comparison not possible" with the reason instead of guessing — and say so where the comparison would have been.

**Demonstrated by:** Upload one clear frame and one unreadable one; the pair reports that it could not be compared and why, per the "Comparison not possible" panel in docs/design/screens/states.html.

- **F4.4.1** Handle parse failures during comparison — Return "comparison not possible" when a photo fails to parse, and render the corresponding failure panel on the frontend.

### F4.5 — Manual override and correction capture

*Requirements: B7, B8* · *Blocked by: F4.2*

A user can overturn any automatic determination, and the correction is stored as labelled data for future evaluation and tuning. Ships with the same-item / two-items control and the settled-with-undo state on the conflict card.

**Demonstrated by:** Flip a "same item" verdict to two items, see the receipt total change accordingly, and undo it.

- **F4.5.1** Manual override endpoints and DB storage — Provide API to flip "same item" decisions. Store correction as labelled data.
- **F4.5.2** Implement manual override UI controls — Implement the same-item / two-items control and settled-with-undo state on the conflict card.

### F4.6 — Deduplicated receipt assembly

*Requirements: B3* · *Blocked by: F4.2*

Merge the per-photo extractions of one receipt into a single item list where matched positions appear exactly once, and reconcile the result against the printed total.

**Demonstrated by:** After resolving the overlap, step 2 shows one item list for the receipt with the duplicate collapsed, and its footer agrees with the printed total.

- **F4.6.1** Assemble deduplicated receipt item list — Merge per-photo extractions into a single item list where matched positions appear once, updating totals on backend and displaying cleanly on step 2.

### F4.7 — Upload step 3 — the resolve gate

*Requirements: B7* · *Blocked by: F4.5, F3.4, F3.6, F1.2, F9.4*

The third step of the wizard, and the endpoint behind it: a batch of decisions is applied together and the receipts are committed only once none are outstanding. One queue for everything needing a human across the whole batch — a position caught in two frames, a field below the confidence threshold, a receipt matching one already stored, a missing total — with a counter, and nothing written while any of it is open. Decisions the agent made alone appear settled and reversible in the same queue rather than hidden. Kept as its own feature because it composes flags raised by four features across two epics; the individual verdicts and evidence are theirs. Screen at docs/design/screens/upload-3-resolve.html.

**Demonstrated by:** Upload a batch that raises several kinds of conflict at once, watch "Store receipts" stay disabled while the counter is above zero, settle them one by one, and only then commit the batch.

- **F4.7.1** Resolve gate API — Create a central queue endpoint for outstanding decisions and block saving the batch until all are settled.
- **F4.7.2** Step 3 UI implementation — Implement the third step of the wizard showing the queue and disabling "Store receipts" until empty.

### F4.8 — Receipt list search and filtering

*Requirements: —* · *Blocked by: F3.8*

Filter the receipt list by processing status, by a specific date, month, or a custom date range (including past dates), and search by merchant or item name. Brings the UI elements in the receipts.html header to life.

**Demonstrated by:** Open Receipts, filter by a past month and see only those receipts. Search for a specific merchant and confirm the list restricts to matching receipts.

- **F4.8.1** API and database filtering logic — Add query parameters for date, status, and search to the list_receipts endpoint and implement the SQLAlchemy query logic in ReceiptRepository.
- **F4.8.2** Frontend store and filter controls — Implement date, status, and search input controls. Connect them to the receipt store to trigger API re-fetches when changed.

---

## E5 — Spend Categorization

**BRD sections:** BR-3 · **Phase:** 1 · **Scope:** Diploma

Classifying every line item into a spending category, with a confidence-gated fallback, user correction that the system learns from, and user-defined categories. Covers BRD C1 through C7.

### F5.1 — Default category taxonomy

*Requirements: C1, C2* · *Blocked by: F3.5, F9.4*

Seeded default categories (Groceries, Dining, Transport, Utilities, Health, Entertainment, Other) plus a guaranteed Uncategorized fallback, modelled so custom user categories coexist with defaults. Ships with the read-only taxonomy screen that F5.6 later makes editable, so the seeded set is inspectable the day it lands.

**Demonstrated by:** Open Categories and read the built-in list with the item count and total behind each, per the "Built in" section of docs/design/screens/categories.html.

### F5.2 — Automatic item categorization

*Requirements: C1* · *Blocked by: F5.1*

Each parsed line item receives a category and a recorded confidence score, shown against the item wherever line items are displayed.

**Demonstrated by:** Upload a grocery receipt and find each line carrying a category chip on step 2 of the wizard and in the receipt detail dialog.

### F5.3 — Confidence threshold, Uncategorized fallback and the review queue

*Requirements: C2, C3* · *Blocked by: F5.2*

Below-threshold classifications become Uncategorized and are flagged for review rather than guessed at — with the queue that collects them, oldest first. Screen at docs/design/screens/categorisation.html.

**Demonstrated by:** Upload a receipt with an obscure item name and find it waiting in the review queue marked Uncategorized, rather than filed under a confident guess.

### F5.4 — Manual category reassignment

*Requirements: C4* · *Blocked by: F5.3*

Any line item's category can be changed by its owner, and the override is recorded as manual so later automatic passes do not overwrite it. Adds the inline picker to the queue and to every other place a line item is shown.

**Demonstrated by:** Reassign an item from the queue, then re-run categorisation and confirm your choice survives — the override is respected, not overwritten.

### F5.5 — Learning from corrections

*Requirements: C5* · *Blocked by: F5.4*

A correction creates a rule applying to future items with the same or highly similar name from the same merchant, which requires a defined similarity measure and a precedence order against automatic classification.

**Demonstrated by:** No screen of its own — it is proven through F5.4's. Reassign "Protein Bar XL" from Fresh Market to Health with "apply to future items" ticked, upload another Fresh Market receipt containing it, and find it already filed under Health.

### F5.6 — User-defined custom categories

*Requirements: C6, C7* · *Blocked by: F5.1, F5.4*

Users can create their own categories, immediately available for both manual and automatic assignment, including the behaviour when a category in use is renamed or deleted. Makes F5.1's taxonomy screen editable.

**Demonstrated by:** Create "Pet Supplies", file items under it, then delete it and choose where those items land — per the delete dialog in docs/design/screens/categories.html.

### F5.8 — Seed script for local sample data

*Requirements: —* · *Blocked by: F1.1, F3.5, F5.1*

A demo user with a handful of categorised receipts spanning two months, plus the `seed` task-runner target that invokes it — enough to exercise the monthly-budget and statistics epics without uploading photos. Lands here, at the end of E5, because this is the first point where every entity it writes exists: User (F1.1), receipt and line items (F3.5) and categories (F5.1). It was originally planned in E0's local development environment, where none of those had been built yet.

**Demonstrated by:** Run `seed`, sign in as the demo user, and find two months of categorised receipts already there — which is what makes E6 and E7 workable without photographing anything.

### F5.9 — A new category from where one is chosen

*Requirements: C6* · *Blocked by: F5.6*

Adding an expense with no fitting category meant leaving the form for Categories and starting again. Where a category is chosen, the last choice adds one: its name is asked in place, the category is made as on the Categories screen and is chosen at once.

**Demonstrated by:** Add an expense "YouTube" by hand, pick "＋ New category", type "Subscriptions": the expense is saved under it, and Categories lists it.

- **F5.9.1** A "＋ New category" in the category choice — The manual expense, the receipt edit and the line item's category picker end their list with "＋ New category", which asks the name in place (the same rules and errors as the Categories screen — a name already used says so) and selects the new one. Three languages; checked at 375, 768 and 1280 px.

---

## E6 — Monthly Budget Calculation

**BRD sections:** BR-4 · **Phase:** 1 · **Scope:** Diploma

Aggregating receipts into monthly totals by transaction date, distinguishing a month-to-date figure from a finalised one, excluding flagged receipts transparently, and recalculating when history changes. Covers BRD D1 through D7.

### F6.1 — Monthly aggregation engine, and the month view

*Requirements: D1, D2* · *Blocked by: F3.5, F9.4*

Sum line-item totals across all receipts whose transaction date — not upload date — falls in the month, which makes back-dated uploads behave correctly. Ships with the figure on screen and the month switcher beside it — the first slice of docs/design/screens/dashboard.html.

**Demonstrated by:** Seed two months (F5.8), open the root route and read this month's total, then step back a month. Upload a receipt dated last month and watch it land in last month's figure rather than this one.

### F6.2 — Transparent exclusion of receipts under review

*Requirements: D3* · *Blocked by: F6.1, F3.4*

Receipts marked "requires manual review" are excluded from the total, and the summary states how many were excluded and their value, so the number is never quietly wrong.

**Demonstrated by:** With a flagged receipt in the month, the month view carries the notice naming how many receipts and how much money sit outside the total, with a way through to fix them.

### F6.3 — Month-to-date versus finalised presentation

*Requirements: D4* · *Blocked by: F6.1*

An in-progress month is labelled incomplete wherever it appears, so a partial figure is never mistaken for a full one.

**Demonstrated by:** The current month reads "month-to-date, still running" with the days elapsed; step back to a finished month and the label changes to finalised.

### F6.4 — Monthly snapshot generation

*Requirements: D5* · *Blocked by: F6.3*

When a month completes, persist a finalised snapshot (the MonthlySnapshot entity), including how the transition is triggered across user time zones.

**Demonstrated by:** No screen of its own — proven through F6.3's label. Roll the clock past a month boundary and watch that month switch from month-to-date to finalised and stop changing, which only a persisted snapshot makes true.

### F6.5 — Recalculation on receipt change

*Requirements: D6, N3* · *Blocked by: F6.4*

Adding, editing or deleting a receipt in a closed month recalculates and updates the stored snapshot, with the recalculation reflected in the same session.

**Demonstrated by:** Edit the total of a receipt in a finalised month from the receipt detail dialog and watch that month's figure move without a reload.

### F6.6 — Budget limit and percentage of target

*Requirements: D7* · *Blocked by: F6.1, F1.4*

Where a monthly limit is set, express current spend as a percentage of it, including the over-100% case.

**Demonstrated by:** Set a limit in Preferences and watch the progress bar and percentage appear on the month view; push spend past the limit and confirm it reads over-100% in error tone rather than clamping at full, per docs/design/screens/dashboard-dark.html.

### F6.7 — Budget dashboard — composing the landing view

*Requirements: D1, D4, D7* · *Blocked by: F6.6, F5.2, F3.8*

What turns F6.1's month figure into the landing view: the category breakdown beside it and the latest-receipts column next to that, each opening into the screens that own them. Both are already on screen from F6.5, fetched as three requests over the existing endpoints. Kept as its own feature because it composes three epics' data — E6's totals, E5's categories, E3's receipts — and needs the endpoint that returns them together rather than three round trips. The figure, the limit bar, the excluded notice and month switching are already there from F6.1, F6.2, F6.3 and F6.6; this finishes docs/design/screens/dashboard.html rather than starting it.

**Demonstrated by:** Open the root route on a seeded account: spend, limit, breakdown and recent receipts on one screen. Click a receipt to open its dialog, click through to full statistics.

---

## E7 — Statistics, Comparison & Export

**BRD sections:** BR-5 · **Phase:** 1 · **Scope:** Diploma

Category-level insight over arbitrary date ranges, period-over-period comparison, honest empty states, chart-ready output, and data export. Covers BRD E1 through E6 and N6.

### F7.1 — Category statistics engine, and the ranked breakdown

*Requirements: E1, E4* · *Blocked by: F5.2, F9.4*

Total spend, share of overall spend and transaction count per category, ranked from highest to lowest by default — with the screen that shows the ranking. First slice of docs/design/screens/statistics.html.

**Demonstrated by:** Open Statistics on a seeded account and read the table: every category with its total, its share and its item count, biggest first.

### F7.2 — Arbitrary date-range support

*Requirements: E2* · *Blocked by: F7.1*

Statistics for any start and end date, not only calendar months, with inclusive boundary semantics defined once and applied everywhere. Adds the preset chips and the range picker to the screen.

**Demonstrated by:** Ask for 10–24 July specifically and watch the totals narrow to those fifteen days, then switch to a preset and back.

### F7.3 — Period-over-period comparison

*Requirements: E3* · *Blocked by: F7.2*

Absolute and percentage change per category between two periods, including categories present in only one of them and the division-by-zero case. Adds the comparison columns and the note that a running month is compared like for like.

**Demonstrated by:** Turn on comparison against the previous period and read the change column — Dining up 29.5%, Groceries down 8.6% — with the running month compared against the same number of days.

### F7.4 — Empty-period handling

*Requirements: E5* · *Blocked by: F7.2*

A range with no receipts returns an explicit "no data" result rather than a zero-filled report that reads like real information.

**Demonstrated by:** Pick a period before your first receipt and read "no receipts in that period" — not a table of zeroes, per the E5 panel in docs/design/screens/states.html.

### F7.5 — Chart-ready output and the comparison chart

*Requirements: E6* · *Blocked by: F7.3*

A response shape the client can render directly, so presentation logic does not re-derive aggregates — and the grouped bar chart that consumes it.

**Demonstrated by:** The chart above the table shows both periods side by side per category, and moves when the range changes.

### F7.6 — Data export

*Requirements: N6* · *Blocked by: F7.1*

CSV and JSON export of the user's receipts, line items and statistics, generated asynchronously for large histories, reachable from where the numbers are.

**Demonstrated by:** Export from Statistics and from Receipts, and open the file — the figures match what the screen showed.

---

## E8 — Goals & AI Optimization Advice

**BRD sections:** BR-6 · **Phase:** 1 · **Scope:** Diploma

The product's differentiator: a user states a financial or lifestyle goal and receives specific, evidence-based, quantified recommendations tied to their own purchase history, with proactive warnings and a feedback loop. Covers BRD F1 through F9.

### F8.1 — Goal definition, storage and the goals screen

*Requirements: F1* · *Blocked by: F1.2, F9.4*

Model both financial goals (savings target, category reduction, overall ceiling) and lifestyle goals (lose weight, save for a car) in one schema without collapsing the distinction that F9 depends on — and the screen that states them. First slice of docs/design/screens/goals.html.

**Demonstrated by:** Set "stay under 3 000 PLN a month" and "lose weight" as goals, see them both on the Goals screen, and edit one.

- **F8.1.1** Goal database model and migration — Implement the Goal SQLAlchemy model containing type (financial vs lifestyle), target amounts, category references, and text descriptions. Write an Alembic migration to add the goals table with a user_id foreign key, enforcing per-user isolation.
- **F8.1.2** Goal API endpoints (CRUD) — Create GET, POST, PATCH, DELETE /api/v1/goals endpoints. Enforce cross-user isolation so users can only access their own goals. Include cross-user access tests in the suite per F1.3.3.
- **F8.1.3** Goals frontend store and API integration — Generate the OpenAPI client. Implement GoalsStore using MobX to fetch, create, edit, and delete goals, following the observable-vs-derived conventions.
- **F8.1.4** Goals screen UI — Build the Goals screen at /goals implementing docs/design/screens/goals.html. Include the "New goal" dialog and the list of active goals as cards with edit actions.

### F8.2 — Lifestyle goal to spending mapping

*Requirements: F9* · *Blocked by: F8.1, F5.1*

Translate a non-financial goal into the relevant categories and recurring items before any advice is generated, since the rest of the pipeline reasons over spend. The goal card shows what it decided to watch, and lets you correct it.

**Demonstrated by:** The "lose weight" card lists the spending lines it maps to — sweets, snacks, sugary drinks, alcohol — and you can adjust that list rather than guess at it.

- **F8.2.1** Goal mapping AI port and prompt — Create a prompt and Claude API adapter that translates a lifestyle goal text into a list of spending categories and matching keywords/items.
- **F8.2.2** Map goals on creation/update — Call the mapping port when a lifestyle goal is created or updated, and save the mapped categories/items to the database as part of the goal record.
- **F8.2.3** Display and edit goal mappings in UI — Update the goal card to show the spending lines it maps to. Allow the user to edit the mapped categories and items.

### F8.3 — Spend analysis for advice

*Requirements: F2* · *Blocked by: F8.2, F7.1*

Identify highest-spend categories, largest recent increases, and recurring positions most relevant to the stated goal — the evidence every recommendation must cite.

**Demonstrated by:** No screen of its own — it is the input F8.4 cites. Proven when a recommendation names "9 of your 14 Fresh Market receipts", a claim only this analysis can supply.

- **F8.3.1** Statistics extraction for goal analysis — Create a service that collects relevant category totals, recent increases (period over period), and frequent line items matching a goal's targets.
- **F8.3.2** Context builder for advice generation — Format the extracted historical data into a structured prompt context to be fed into the advice generation AI.

### F8.4 — Recommendation generation and the advice feed

*Requirements: F3* · *Blocked by: F8.3*

Produce specific, actionable recommendations naming a category or an individual recurring item. Constraint 11.3 rules out generic financial tips, so genericness is a defect to be tested for, not a style preference. Ships with the advice feed that carries them.

**Demonstrated by:** Ask for advice on a seeded account and read a recommendation naming an actual item you actually buy — not "consider reducing discretionary spending".

- **F8.4.1** Advice generation prompt and AI port — Write a prompt enforcing non-generic, specific recommendations based on the spend analysis context. Implement the AI adapter to call Claude.
- **F8.4.2** Recommendation endpoints — Add an endpoint to trigger advice generation for a goal and another to list generated recommendations. Store generated recommendations in the database.
- **F8.4.3** Advice feed UI — Build the advice feed section below goals in docs/design/screens/goals.html to display the generated recommendations.

### F8.5 — Projected impact quantification

*Requirements: F4* · *Blocked by: F8.4*

Every recommendation states its expected effect on the goal, computed from the user's actual history rather than asserted by the model.

**Demonstrated by:** Each advice card carries its figure — "−61.20 PLN a month", "−64% of sweet purchases" — and the arithmetic can be checked against the receipts behind it.

- **F8.5.1** Compute projected impact mathematically — Ensure the backend calculates projected impact strictly from historical data rather than trusting AI hallucinated numbers, and includes this in the recommendation payload.
- **F8.5.2** Display impact figures on advice cards — Render the calculated impact values on the recommendation cards in the advice feed.

### F8.6 — Insufficient-data guard

*Requirements: F5* · *Blocked by: F8.4*

Below a configured minimum of history, say more data is needed instead of emitting a low-confidence recommendation.

**Demonstrated by:** Ask for advice on a fresh account with three receipts and read that more history is needed, per the F5 panel in docs/design/screens/states.html — no invented advice.

- **F8.6.1** Enforce minimum data threshold in advice generation — Check if the user has sufficient history (e.g., minimum number of receipts or months) before generating advice. Return an explicit insufficient-data status if not.
- **F8.6.2** Insufficient data UI state — Show the "more history needed" state panel (F5 panel from states.html) when the backend indicates insufficient data.

### F8.7 — On-track progress reporting

*Requirements: F6* · *Blocked by: F8.4, F6.6*

When pace meets the goal, report positive progress and explicitly suppress unnecessary cuts.

**Demonstrated by:** With spend on pace to finish under the ceiling, the feed leads with "nothing to cut this month" and the projected finish, and offers no savings advice for that goal.

- **F8.7.1** Detect on-track status during generation — Evaluate the spending pace against the goal before generating advice. If on pace, skip generating cuts and output an "on track" message.
- **F8.7.2** Render on-track status in UI — Display the positive progress card ("nothing to cut this month") when the user is on track, suppressing normal advice cards.

### F8.8 — Proactive at-risk warnings

*Requirements: F7* · *Blocked by: F8.7*

Detect mid-month that projected spend will miss the goal and surface a warning with at least one corrective recommendation before the month ends — this requires scheduled evaluation and a delivery channel, not just a request handler.

**Demonstrated by:** Push mid-month spend onto a pace that overshoots the ceiling and find the warning waiting without having asked for it, with at least one way to correct course.

- **F8.8.1** Background task for proactive evaluation — Implement a scheduled background job to evaluate goals mid-month and generate at-risk warnings if projected spend overshoots.
- **F8.8.2** Display at-risk warnings in dashboard and goals — Fetch and prominently display proactive warnings in the dashboard and goals screens.

### F8.9 — Recommendation feedback loop

*Requirements: F8* · *Blocked by: F8.4*

Capture "not followed" and "not helpful" feedback and deprioritise similar recommendations in later generations, through controls on the advice itself.

**Demonstrated by:** Mark a Dining recommendation "not for me", ask for advice again, and find similar Dining suggestions demoted and the dismissed one shown as such with an undo.

- **F8.9.1** Recommendation feedback endpoints — Add endpoints to submit feedback (not helpful, not followed) for a recommendation and save it to the DB.
- **F8.9.2** Feed feedback into advice context — Include dismissed/unhelpful recommendation history in the prompt context to ensure Claude avoids suggesting similar cuts.
- **F8.9.3** Feedback UI controls — Add feedback action buttons to advice cards and handle the UI state (e.g. graying out dismissed cards with an undo option).

### F8.11 — Goals that show where they stand

*Requirements: F1, F3, F6* · *Blocked by: F8.9, F23.13, F23.14*

The goals audit of 2026-10-21 found goals that are set and then say little. A savings goal has no date ("3 000 for a holiday by June" loses "by June") and no progress at all; a monthly ceiling or category cut shows its pace only inside the advice block or an at-risk warning; a lifestyle goal shows no progress. Advice often ends in "your receipts show nothing specific to act on": proposals are kept only when their target name matches the evidence exactly, and the model writes them in the user's language, so a translated category or product name drops every one (to be confirmed by the test below). Every goal card leads with where it stands, and advice names what it found.

**Demonstrated by:** A savings goal of 3 000 by June shows 1 200 saved and 600 a month needed; a ceiling shows this month's bar; in Ukrainian, advice on a restaurants goal names the restaurants it found instead of "nothing specific".

- **F8.11.1** A savings goal with a date and money saved — An optional date on a goal (add-only migration, ADR-0014); a savings goal's saved amount from a card the user picks for it (F23.15) or, without cards, an amount they enter and update; the card shows saved of target, the date and what is needed a month to reach it, and says when the date has passed. The goal check (F23.13) judges against the date when there is one. Checked at 375, 768 and 1280 px.
- **F8.11.2** Progress at the top of every goal card — A ceiling and a category cut show this month's spent, the cap and the projected finish as a bar (from the existing pace), a lifestyle goal its watched lines this month against the average of the last three; on track or at risk said in one line; the advice block below unchanged. One progress endpoint for every kind, which the assistant reads too (F21.5). Checked at 375, 768 and 1280 px.
- **F8.11.3** Advice that finds what is there — A test reproducing "nothing specific" with advice in Ukrainian and Polish; the evidence given to the model with ids and the model returning the id of what it targets, so the check no longer depends on how a name is written; when nothing is found after all, the answer says what was looked at (categories, products, months). Each ask counts in the AI limit (F21.9).

---

## E9 — Web Client Foundation

**BRD sections:** — · **Phase:** 1 · **Scope:** Diploma

The React and MobX groundwork every feature screen builds on. Deliberately separated so that state, API access and layout conventions are decided once rather than reinvented in each feature epic. Scope rule: only what has no domain dependency belongs here. Screens for a capability ship inside that capability's own epic — this epic is the shared floor they stand on, not "the frontend half" of the product. Built before E1 despite its number, because nothing in it waits on an endpoint; see `depends_on` for the real order.

### F9.1 — React, Vite and TypeScript project setup

*Requirements: —*

Strict TypeScript, path aliases, ESLint and Prettier matching the backend's rigour, and Vitest with React Testing Library.

- **F9.1.1** Scaffold the Vite + React + TypeScript project — Vite's react-ts template under frontend/, strict TypeScript (mirrors the backend's mypy --strict) with no implicit any, and a `@/` path alias resolved consistently in both tsconfig.json and vite.config.ts.
- **F9.1.2** ESLint and Prettier matching backend lint rigour — Flat ESLint config with typescript-eslint strict rules, react-hooks, and jsx-a11y (enforces the semantic-HTML convention below). Prettier for formatting. Both wired into the repository's pre-commit alongside ruff and mypy.
- **F9.1.3** Vitest and React Testing Library harness — Vitest with the jsdom environment, RTL plus jest-dom matchers, and a `test` script. A smoke test rendering App proves the harness runs in CI (F0.5).
- **F9.1.4** Establish the src/ folder structure — src/pages, src/components (feature-scoped), src/shared/components, src/shared/styles, src/stores, src/api and src/routes, documented in frontend/README.md with the rule for shared/ versus feature-local: a component or style used by more than one feature, with no feature-specific business logic, belongs in shared/.

### F9.2 — MobX store architecture and conventions

*Requirements: —*

Root store composition, dependency injection into components, the rule for what is observable versus derived, and async action conventions. Written down as a short guide, because this is the decision later epics will otherwise each make differently.

- **F9.2.1** Root store composition and context injection — A single RootStore instantiated once and provided through a React context with a useStores() hook. No component or feature store reaches for another store via a direct import — DIP applies to frontend state the same way it applies to the backend's ports.
- **F9.2.2** Observable-vs-derived and async-action conventions — Document when a field is `observable` versus a computed `get`, and the idle/loading/success/error status-flag shape every async action follows, so a reader recognises the pattern in any store without re-deriving it.
- **F9.2.3** ThemeStore for light/dark mode — Persists the theme preference to localStorage, defaults to the OS prefers-color-scheme, and toggles the `.dark` class the color tokens (F9.6) key off — same responsibility as budget-checker's ThemeStore.

### F9.3 — Generated API client from OpenAPI

*Requirements: —*

TypeScript types and client generated from the FastAPI schema in CI, so a backend contract change breaks the frontend build rather than production.

- **F9.3.1** Backend OpenAPI schema export script — backend/scripts/export_openapi_schema.py imports create_app() and writes app.openapi() as JSON to stdout. Schema generation is pure route/model introspection — no environment variables and no database connection required — so it runs the same way locally and in CI. The single source both the frontend codegen and the CI drift check read from.
- **F9.3.2** Generated types and typed client wired into npm scripts — openapi-typescript generates frontend/src/api/schema.ts (checked in, not hand-edited) from the backend's exported schema via `npm run generate:api`. openapi-fetch provides the runtime client in frontend/src/api/client.ts, typed against those generated paths, with its base URL read from the VITE_API_BASE_URL env var. This is the only module a store may import to reach the backend — see the frontend/backend boundary rule in docs/architecture/overview.md.
- **F9.3.3** CI check that the checked-in client matches the current schema — frontend-ci.yml also triggers on backend/app/** changes and regenerates src/api/schema.ts before the build, failing the job (git diff --exit-code) if the regenerated file differs from what's committed. A backend contract change with no matching frontend regeneration fails CI instead of surfacing as a runtime mismatch in production.

### F9.4 — Application shell and navigation

*Requirements: —* · *Blocked by: F9.1, F9.6*

The static frame every screen renders inside, plus something to see at the root before an account exists. Deliberately excludes the authenticated route table, the guard and the expiry redirect — those need F1's session model and ship with it in F1.2.6. What remains has no domain dependency, so it lands before any endpoint does and gives E1's screens a frame to arrive into.

**Demonstrated by:** Open the root route signed out and land on a real screen with working links to sign in and register, inside the shell every later screen will use.

- **F9.4.1** Application shell — header, navigation and content container — The frame every screen renders inside: header with the brand and theme toggle, the navigation row, and the responsive content container. Anatomy and spacing come from docs/design/components.md, colours from the tokens in F9.6.1. No global footer — login and register carry a one-line privacy strip and no other screen has one, so there is nothing to share yet.
- **F9.4.2** Public landing screen at the root route — What an unauthenticated visitor sees at /: the brand header, one sentence on what the product does, and two actions — sign in, create an account. Deliberately minimal; the BRD asks for no marketing page, and this exists so the root is not blank and the shell has a real screen to prove itself against. Once a session exists the same route belongs to F1.1.7.
- **F9.4.3** Router with the public route table — react-router mounted with the public routes only — landing, login, register — and a not-found route. The authenticated table and the guard in front of it are F1.2.6's, so this task must not invent a placeholder guard for them.

### F9.6 — Component primitives and design tokens

*Requirements: —* · *Blocked by: F9.1*

Buttons, forms, tables, modals, currency and date formatting bound to the account currency, and the token set they draw from. The values are already fixed by docs/design/design.css — this feature ports them into the app, it does not choose them again (ADR 0004).

**Demonstrated by:** Toggle the theme on any screen and watch every colour follow from the tokens, then compare a button against docs/design/screens/design-language.html.

- **F9.6.1** Color-token system ported from budget-checker — Tailwind v4 with a `@theme` layer over semantic CSS custom properties (--color-background, --color-primary, etc.) in src/shared/styles/colors.css, light values on :root and dark overrides on .dark. One source of truth per DS-1: components reference tokens (bg-primary, text-foreground), never a raw hex.
- **F9.6.2** Responsive breakpoint tokens (mobile / tablet / desktop) — Named breakpoint tokens in src/shared/styles/breakpoints.css and a mobile-first convention: base styles target mobile, md:/lg: Tailwind variants layer up tablet and desktop. No shared component ships a fixed pixel width.
- **F9.6.3** Reusable primitive component library — src/shared/components/ — Button, Input, Select, Modal, Table, Card — each typed, each built only from the tokens above. A feature screen composes these instead of hand-rolling markup for a UI role that already exists.
- **F9.6.4** Shared layout primitives and style utilities — src/shared/styles/ spacing and typography scale plus layout primitives (Stack, Grid, a responsive Container) reused across breakpoints, so a screen composes layout instead of hand-rolling flexbox per page.

### F9.7 — Loading, empty and error state conventions

*Requirements: —*

One documented treatment for each, so the honest empty states E5 and F5 require are consistent rather than per-screen improvisations. Not yet groomed into tasks: easiest to standardise once a couple of real feature screens exist to generalise from.

**Demonstrated by:** Every empty, loading and refused state in the product matches its panel in docs/design/screens/states.html — checked screen by screen, not asserted.

- **F9.7.1** Implement Loading state component — A generic loading component (e.g. spinner or skeleton) for use while fetching data.
- **F9.7.2** Implement Empty state component — A component for screens with no data, supporting an icon, title, message, and action button.
- **F9.7.3** Implement Error state component — A component for failure/refused states, supporting an error icon, message, and retry button.

### F9.8 — Installable app (PWA)

*Requirements: —* · *Blocked by: F0.9*

The web client installs on a phone's home screen and opens full screen like an app, so photographing receipts does not start with typing an address — without an app store, its fees or its review, and with every deploy reaching installed copies at once. Push notifications are left for a feature of their own: they need a backend to send them and something worth sending.

**Demonstrated by:** On an iPhone, open the production URL in Safari, follow the hint to add it to the Home Screen, and open it from the new icon: full screen, no browser bar, the camera available on Upload. On Android, Chrome offers "Install app" itself. With the network off, the installed app opens to a page saying it is offline instead of a browser error.

- **F9.8.1** Web app manifest and icons — A manifest naming the app, its start URL, standalone display and theme colours from the design tokens; an app icon (also maskable) and an Apple touch icon, added to docs/design; the iOS meta tags that make the installed app full screen. The browser tab gets the same icon.
- **F9.8.2** Service worker for the app shell — Caches the built app so an installed copy opens fast and, without a network, shows an offline page rather than a browser error. Never caches API responses — receipts and figures are financial data and must not linger on the device. A new deploy is picked up on the next launch. Firebase Hosting serves the worker and manifest uncached.
- **F9.8.3** Install hint — Where a browser offers installing (Android Chrome), an "Install app" action in the profile; on iPhone Safari, which never offers it, a short dismissible hint how to add the app to the Home Screen. Nothing shown once installed. Checked at 375, 768 and 1280 px.

### F9.9 — Localization (English, Ukrainian, Polish)

*Requirements: —* · *Blocked by: F9.2*

The product speaks the user's language: English, Ukrainian or Polish, chosen on first visit from the browser's language — never from where the user is, since a Ukrainian living in Poland reads Ukrainian — and changed any time on Profile or, before signing in, on the public pages. The choice is kept with the account, so it follows the user to another device and the server answers in it too. Dates, amounts and plural forms follow the language. Receipts are not translated: merchants and items stay as printed.

**Demonstrated by:** Open the app in a browser set to Ukrainian: the landing page and sign-in are in Ukrainian. Switch to Polish on Profile: every screen follows, "2 paragony" and "5 paragonów" included, and signing in on a phone shows Polish there as well.

- **F9.9.1** Language infrastructure and switchers — i18next with one JSON resource file per screen area under frontend/src/locales/{en,uk,pl}/, English the source whose keys type-check the others; plural forms through Intl.PluralRules. The language is the account's (`users.language`, add-only migration, read and changed through /users/me) or, before signing in, the browser's own choice kept in localStorage; on a first visit, the browser's languages, else English. A switcher on Profile and a compact one on the public pages. Dates and amounts formatted in the chosen language instead of the hard-coded en-GB / en-US. A check in CI fails when a key is missing from uk or pl. Checked at 375, 768 and 1280 px.
- **F9.9.2** Public and sign-in screens in three languages — Landing, sign in, register, the password checklist, the invite page and the app shell (navigation, toasts, not-found) read from the resources, translated into Ukrainian and Polish. Checked at 375, 768 and 1280 px in each language.
- **F9.9.3** Upload and receipts in three languages — The upload wizard, the receipts list, the receipt view and its dialogs, read from the resources and translated. Checked at 375, 768 and 1280 px in each language.
- **F9.9.4** Dashboard, statistics, categories, goals and profile in three languages — The remaining screens, read from the resources and translated; built-in category names translated by key, the user's own as they named them. Checked at 375, 768 and 1280 px in each language.
- **F9.9.5** Server messages and advice in the user's language — Refusals the user reads get their own problem codes and their values as `params` beside the English `detail`; the client shows its translation of the code and falls back to `detail` for a code it does not know. Goal advice is written in the user's language. Tests that every code the server can send has a translation.

---

## E10 — Security, Privacy & Observability

**BRD sections:** N1, N2, N3, N5 · **Phase:** 1 · **Scope:** Out of scope

The cross-cutting non-functional requirements from BRD section 8 and the constraints in section 11, given their own epic so they are scheduled work rather than assumed work.

### F10.1 — Encryption at rest for images and extracted data

*Requirements: N1*

Receipt images and the extracted financial fields are encrypted at rest, with a documented key management and rotation approach.

**Demonstrated by:** No screen of its own — receipt photos and totals keep rendering exactly as before, which is the point. Proven at the storage layer and by rotating a key without any screen changing.

### F10.2 — Access control verification

*Requirements: N2*

An automated suite covering every user-owned endpoint, extending the base suite from F1.3 as each epic adds resources.

**Demonstrated by:** No screen of its own. Proven by the suite failing when a new endpoint is added without an ownership filter — the check that F1.3's guarantee stays true as the product grows.

### F10.3 — Receipt deletion and cascade

*Requirements: N3*

Deleting a receipt removes it from budget and statistics results within the same session, including its effect on any finalised snapshot.

**Demonstrated by:** Delete a receipt from its detail dialog and watch the month total and the category breakdown both move without a reload.

### F10.4 — Classification decision audit log

*Requirements: N5*

Every automatic category assignment and position-match decision logged with its confidence score, supporting both auditing and the tuning that C5 and B8 imply.

**Demonstrated by:** No screen of its own — it records what the screens already show. Proven by categorising a receipt and finding each decision and its confidence in the log.

### F10.5 — Structured logging, metrics and tracing

*Requirements: —*

Correlated request logging with financial values redacted, plus the latency metrics needed to prove the N4 target is met.

**Demonstrated by:** No screen of its own. Proven by uploading a receipt, following one request id from the browser through every service log, and finding no amounts in any of them.

### F10.6 — Rate limiting and abuse protection

*Requirements: —* · *Blocked by: F0.9* · *Scope: Diploma, unlike its epic*

Upload and AI-backed endpoints are the expensive ones; limit them per account and define the behaviour when a limit is hit. Each account gets a monthly number of receipt reads, configurable without a release; admins have none. Expensive and abusable endpoints are rate-limited per IP, and a service-wide daily ceiling on model calls caps the bill whatever happens to the per-account limits.

**Demonstrated by:** On a phone, upload receipts as an ordinary account and watch "8 of 10 receipts left this month" count down; past the limit the upload screen says what the limit is and the date it resets, rather than a bare 429. Signed in as the admin, the same screen says there is no limit.

- **F10.6.1** Monthly receipt-reading quota per account — Each account may have at most `monthly_receipt_quota` receipts read per calendar month (UTC, ADR-0009), default 10, set by environment variable. A receipt counts when it is read, not when it is stored, because the model call is the cost: receipts in upload jobs started this month plus emailed receipts. An upload that would exceed it is refused before any model call with a `quota_exceeded` problem stating the limit and the reset date; emailed receipts over it are dropped and logged. GET /users/me/quota returns limit, used, remaining, reset date and whether the account is unlimited.
- **F10.6.2** Admin accounts without limits — An account is an admin when its role is `admin` or its email is listed in `admin_emails` (environment, set from Terraform). Admins have no receipt quota and no service-wide ceiling. Being an admin grants no access to another user's data (BRD N2, G8).
- **F10.6.3** Per-IP rate limits on expensive endpoints — Registration, receipt upload, asking for advice and exports are limited per client IP (Cloud Run passes it in X-Forwarded-For), alongside the existing login limit. A limit hit is a 429 in the RFC 7807 envelope with the retry delay, never the library's default body.
- **F10.6.4** Service-wide daily ceiling on receipt reads — At most `daily_receipt_read_ceiling` receipts are read per UTC day across all non-admin accounts, so the bill is bounded even if the per-account quota is misconfigured or many accounts are created. Over it, uploads are refused with a `service_busy` problem saying when to try again. Vertex AI quotas cannot serve this: Gemini 2.x runs on a shared dynamic quota with no per-project cap.
- **F10.6.5** Quota on the upload screen and the profile — The upload screen shows how many receipts are left this month, and past the limit explains the limit and the reset date instead of offering to upload; the profile shows the month's usage; an admin sees that there is no limit. Checked at 375, 768 and 1280 px.

---

## E11 — Alternative Receipt Intake

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

BRD section 10 assumes every receipt arrives as a photograph. That assumption is the product's largest retention risk: photographing receipts is effort the user has to repeat every week, and repeated effort is what stops budgeting apps being opened after the second week. This epic adds intake that costs the user nothing — e-receipts arriving by email, the fiscal QR code printed on the receipt, and national e-receipt services — behind the same ingestion pipeline, so the channel changes only how a receipt arrives and nothing downstream of it.

### F11.1 — Intake channel abstraction

*Requirements: A12, A15*

One ingestion port with an adapter per channel, so adding a channel does not touch parsing, categorisation or budget calculation. Every receipt records the channel it arrived through and the source reference, because a support question about a wrong figure starts with where the data came from. Photo upload becomes the first adapter; its behaviour does not change.

**Demonstrated by:** No new screen of its own: upload a receipt photo exactly as before and confirm it, and the receipt's detail view says it was added from a photo.

- **F11.1.1** Extend Receipt model with channel metadata — Add `channel` (enum: photo, email, qr) and an optional `source_reference` to the Receipt model and response schema, with an Alembic migration that marks every existing receipt as a photo. Further values arrive with the channel that needs them (F11.4's e-receipt service among them), not ahead of it.
- **F11.1.2** Define Receipt Ingestion Port — Create a `ReceiptIngestionPort` protocol, typed by the payload its channel receives, that turns one receipt's raw input into one extraction for the existing categorisation and review pipeline.
- **F11.1.3** Refactor photo upload to use Ingestion Port — Move photo storage and vision extraction into a photo adapter implementing the port. A pure move: same storage keys under the owner's prefix (N2), same merging of overlapping shots (B2-B4), same failure reporting; the existing tests pass unchanged in what they assert.
- **F11.1.4** Carry the channel from intake to the stored receipt — The adapter states its channel and source reference; the upload job keeps them and the confirmed receipt is stored with them, so a second channel records itself rather than silently landing as a photo.
- **F11.1.5** Show how a receipt arrived — The receipt detail view shows the channel ("Added from a photo") and, where there is one, the source reference. Checked at 375, 768 and 1280 px.

### F11.2 — Email receipt ingestion

*Requirements: —* · *Blocked by: F11.1*

A per-user forwarding address that accepts electronic receipts, extracting items from HTML bodies and PDF attachments. Sender verification matters here: an intake address is a public endpoint that writes to a user's financial record.

**Demonstrated by:** In Profile, copy your receipt forwarding address and forward a store's e-receipt to it from the email you signed up with: the receipt appears on Receipts marked "From email", itemised and categorised like a photo. The same forward from an unknown sender adds nothing.

- **F11.2.3** Decide the inbound email provider — ADR choosing how inbound mail reaches the backend without a paid domain — App Engine's inbound mail on `<project>.appspotmail.com` relayed to a webhook (ADR-0013) — and fixing the limits a public intake address needs: message size, accepted attachment types, and a per-user daily rate. Includes the local SMTP relay that stands in for it in docker compose.
- **F11.2.4** Per-user forwarding address — Give each user an unguessable forwarding address, stored with the user, that can be regenerated to stop spam reaching it; the old address stops accepting mail at once. Exposed to the user's own profile only (N2).
- **F11.2.1** Configure email ingestion webhook — Receive raw messages from the relay behind a shared secret, resolve the forwarding address to its user, and accept only mail from that user's account email, within the daily limit. Rejected mail is logged and dropped, never stored. The App Engine receiver itself is deployed with the Google Cloud infrastructure (F0.9).
- **F11.2.2** Implement email parsing and adapter — An email adapter implementing `ReceiptIngestionPort`: read the receipt from the HTML body or a PDF attachment through the existing parser, with the message id as the source reference. The receipt lands in the same review flow as a photo.
- **F11.2.5** Forwarding address and email receipts in the UI — Profile shows the forwarding address with copy and regenerate, and how to forward a receipt to it. Receipts marks email receipts and can be filtered by how they arrived. Checked at 375, 768 and 1280 px.

### F11.3 — Fiscal identity of a receipt

*Requirements: A12, A14* · *Blocked by: F11.1, F11.4*

Every fiscal receipt prints numbers that identify it uniquely — in Poland the cash register's number (ECA …) and the printout number, in Ukraine the register's and the receipt's fiscal numbers. The reader takes them off the photo, and they are stored with the receipt. This replaces the planned QR intake: the F11.4 spike (ADR-0015) found that neither market lets a third-party app fetch a receipt's items, and Polish receipts carry no fiscal QR code at all.

**Demonstrated by:** Upload a Polish shop receipt: the receipt view shows "Register ECA 2201079960 · receipt 85503". A restaurant bill without fiscal numbers shows none, and nothing else changes.

- **F11.3.1** Read and store the fiscal identity — The reader returns the register number and the receipt number, normalised; they are stored on the receipt, from the wizard and from email alike, indexed per user. A receipt without them stores none. Parser version bumped.
- **F11.3.2** Show the fiscal identity on the receipt — The receipt view shows the register and receipt numbers when the receipt has them. Checked at 375, 768 and 1280 px.

### F11.4 — National e-receipt service integration

*Requirements: —*

A feasibility spike on integrating with the target markets' e-receipt systems (e-Paragony in Poland, єЧек in Ukraine) and on fiscal QR codes. Answered by ADR-0015: neither is open to a third-party app today, so there is no integration to build; the receipt's printed fiscal identity (F11.3) is used instead.

**Demonstrated by:** No screen of its own: proven by ADR-0015, which records for Poland and Ukraine what a fiscal QR code holds, why its items cannot be fetched, and what to watch for that would reopen the question.

- **F11.4.1** Spike e-receipt system integration — Research integration feasibility with national e-receipt services and with fiscal QR codes in Poland and Ukraine. Produce an ADR with findings and architectural decisions, and the follow-up tasks for F11.3 and F11.4.

### F11.5 — Cross-channel duplicate detection

*Requirements: A14* · *Blocked by: F11.2, F11.3*

One purchase that arrives twice — photographed twice, or photographed and emailed — is one receipt. BRD A14 compares merchant, date and total, which cannot tell a second copy apart from a second visit to the same shop on the same day; the fiscal identity can.

**Demonstrated by:** Upload a receipt already stored: the wizard says "Already stored — added 3 October" and does not store it again, without asking. Forward the e-receipt of a restaurant bill you already photographed: Receipts marks the new one as a possible duplicate, and you keep both or remove it.

- **F11.5.1** Recognise a receipt already stored by its fiscal identity — A receipt whose register and receipt numbers match one of the user's stored receipts is not stored again — in the wizard it is shown as already stored, with when it was added, and left out of the commit; by email it is dropped. Without a fiscal identity, merchant, date and total still ask the user (A14). A duplicate the user chose to skip is never stored.
- **F11.5.2** Confirm a cross-channel duplicate outside the upload flow — Email receipts arrive without the wizard, so a likely duplicate by merchant, date and total is stored marked as possibly the same as an earlier receipt; Receipts shows the mark, and the receipt view offers to keep both or remove the new one. Checked at 375, 768 and 1280 px.

### F11.7 — Receipts in a foreign currency

*Requirements: D1* · *Blocked by: F11.1*

A receipt from a trip abroad — hryvnias on a złoty account — is converted into the account's currency at the rate of its purchase date, instead of being counted as if 1197 UAH were 1197 PLN. The original amount, currency and rate stay on the receipt, so the figure can always be traced back. Until now the reader recognised the currency and the app dropped it, which overstated a month roughly tenfold; the BRD had multi-currency down as a non-goal, and this feature reverses that, with an ADR.

**Demonstrated by:** On a złoty account, upload a Ukrainian receipt: the wizard shows "1197.00 UAH ≈ 115.40 PLN · NBP rate, 3 October"; once stored, the month total and the statistics count 115.40, and the receipt shows both amounts.

- **F11.7.1** Decide how foreign receipts are converted — ADR: a free, keyless rate source that covers any account currency and any receipt currency, wherever the user lives — the National Bank of Poland's tables A (daily) and B (weekly, the rarer currencies), crossed through the złoty for accounts in other currencies, with the ECB rates (Frankfurter) as the fallback; verify both cover UAH and USD before deciding. Also the rate date (the purchase date, else the last published rate before it), rounding, and that the rate is stored with the receipt so totals never shift afterwards. Updates the BRD non-goal and answers the domain model's open question on multi-currency.
- **F11.7.2** Exchange-rate port with cached rates — An ExchangeRatePort with NBP and ECB adapters, converting between any two currencies they cover (crossing through a common one where needed, e.g. UAH → PLN → USD for a dollar account); each rate fetched is cached in the database by currency pair and date, so a month of receipts costs a handful of calls. Tests stub the port; a rate service that cannot answer raises one error type the caller handles.
- **F11.7.3** Store the original amount and convert on intake — A receipt keeps its original currency, original total and the rate and its date; its line totals are stored in the account's currency so every total, statistic and budget figure stays one currency (D1). Conversion happens when a receipt is stored, whether through the wizard or by email. With no rate available the receipt is held in review saying why, never stored as if it were in the account's currency.
- **F11.7.4** Show both amounts — The wizard and the receipt view show the original amount beside the converted one with the rate's source and date; the receipts list shows the converted total with the original currency marked. Checked at 375, 768 and 1280 px.

---

## E12 — Household & Shared Budgets

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

BRD section 4.2 places shared budgets out of scope and section 14 leaves the question open. Commercially they are what makes the product stick: a household that has agreed a shared budget does not churn the way one person tracking their own spending does. Groomed on 2026-10-09 around the cheapest model that delivers it: a receipt stays its owner's, and belonging to a household only adds read access to the other members' receipts, so N2, every repository and every access test written so far keep working unchanged. Goals and advice stay personal.

### F12.1 — Ownership model decision

*Requirements: N2*

A receipt is owned by the user who added it; a household is a group of users, and membership grants read access to the members' shared receipts, never write access. Decided and written up before any schema changes, because it constrains every repository already written.

**Demonstrated by:** No screen of its own: the ADR in docs/adr/ that every later E12 feature is built on.

- **F12.1.1** Decide how a household shares receipts — ADR: receipts stay owned by their user (user_id unchanged); one household per user; members read each other's shared receipts and only the owner edits or deletes; joining shares everything except receipts marked private; a private receipt's money still counts in the household's totals, but the household sees only one line per member per month ("Private — Anna: 120 PLN") with no merchant, items, category or date; members must share one account currency, since household totals are in it (ADR-0016). Updates the BRD out-of-scope note, the domain model's open question on households and invariants for the household, and overview.md.

### F12.2 — Household and its members

*Requirements: —*

A household, the users in it, and two roles: the owner, who created it and may rename it, set its budget and remove members, and members, who may leave.

**Demonstrated by:** On Profile, create a household and give it a name; it lists you as its owner. A second account that joins (F12.3) appears in the list; the owner can remove it, and a member can leave.

- **F12.2.1** Household and membership — Household (name, owner) and HouseholdMember (household, user, role, joined_at), with a migration that only adds. Endpoints to create, read, rename, leave, and for the owner to remove a member. A user belongs to at most one household; the owner leaving with members left is refused until they remove them, and the last member leaving deletes it. Cross-household tests (N2): a non-member reads nothing and changes nothing.
- **F12.2.2** Household on Profile — Profile gains a Household card: create one, see its name and members with their roles, rename and remove members as owner, leave as member, each with a confirmation. Checked at 375, 768 and 1280 px.

### F12.3 — Joining by invite link

*Requirements: —*

Joining by a link the owner shares however they like, so no mail provider is needed. The link can be regenerated, which stops the old one working.

**Demonstrated by:** The owner copies the household's invite link from Profile and sends it by messenger; the other person opens it, signs in or registers, and joins after confirming.

- **F12.3.1** Invite codes — The household carries an unguessable invite code the owner can read and regenerate. Joining by code adds the user as a member unless they are already in a household or their account currency differs from the household's, each refused with a reason; a regenerated code invalidates the old one. Joining is rate-limited per IP like login (F10.6). Tests for each refusal.
- **F12.3.2** Invite link and join page — The Household card shows the invite link with copy and regenerate. /join/:code shows the household's name and owner and a Join button; an anonymous visitor is sent to sign in or register and returned to it. Refusals are shown in words. Checked at 375, 768 and 1280 px.

### F12.4 — Shared and private receipts

*Requirements: N2*

A member's receipts are shared with the household from the moment they join, except those they mark private. The household sees shared receipts in full and read-only; a private one is never shown, only its money (F12.5).

**Demonstrated by:** In a household of two, Receipts gains a "Mine / Household" switch: the household view lists both members' receipts with who added each, read-only for the other's. Marking a receipt private removes it from the other member's view.

- **F12.4.1** Read access through membership — Receipt gains `is_private` (default false, add-only migration). A household receipts listing returns the members' non-private receipts with who added each, and a member may open one; edit, delete, recategorise and every write stay owner-only through the existing ownership filter. Leaving or being removed revokes access at once. Cross-household tests: a non-member, a removed member and a private receipt are each invisible (N2).
- **F12.4.2** Mark a receipt private — The owner marks or unmarks a receipt private from the receipt view, which says what the household then sees ("only the amount, in your monthly private total"). Absent outside a household. Checked at 375, 768 and 1280 px.
- **F12.4.3** Household view of Receipts — A "Mine / Household" switch on Receipts, shown only in a household; the household view marks whose each receipt is and opens another member's read-only, without edit, delete or category controls. Filters and pagination work as in the personal view. Checked at 375, 768 and 1280 px.

### F12.5 — Household budget and statistics

*Requirements: —*

BR-4 and BR-5 over the household's combined spending, including each member's contribution, which is the number households actually argue over. Private receipts count in the money but never show what they were. Goals and advice stay personal.

**Demonstrated by:** The owner sets a household budget on Profile; the dashboard's "Household" view shows the month's total against it with each member's share, private spending included as one line per member; Statistics shows the household's categories with a "Private" row.

- **F12.5.1** Household month and limit — The owner sets an optional household monthly budget. The household month adds every member's parsed receipts filed in it (D1-D3, same month rules as personal), private ones included, against that budget, and splits the total per member, each member's private receipts summed into one figure with no date or detail. Tests that a private receipt changes the totals and nothing else about it is returned.
- **F12.5.2** Household statistics — Category statistics over the household's shared receipts for a period, as the personal ones (E6), with private spending as a single "Private" row; each member's own categories are kept apart by user, so a custom category name is shown with its owner. Tests that no private receipt's category or items leak.
- **F12.5.3** Household dashboard and statistics views — Dashboard and Statistics gain the same "Mine / Household" switch: the household month shows the total against the household budget and a per-member split with private lines; Statistics shows household categories with the Private row. The owner sets the household budget on the Household card. Checked at 375, 768 and 1280 px.

### F12.6 — Access control under shared ownership

*Requirements: N2*

One suite that walks every household-aware endpoint as the owner, a member, a removed member and a stranger, so a later change cannot open one quietly.

**Demonstrated by:** No screen of its own: the cross-household suite in CI, failing if any household endpoint lets a non-member, a removed member or a private receipt through.

- **F12.6.1** Cross-household access suite — A parametrised suite over every endpoint E12 adds or widens: membership grants read only, removal revokes at once, a private receipt's details are never in any response to anyone but its owner, and every write stays owner-only.

### F12.8 — Shared money in the family

*Requirements: —* · *Blocked by: F12.5, F23.17, F23.18*

Today an income, a regular bill or the budget one adult sets is invisible to the other: the family's money is not the family's. Each of them is either "mine" or "shared with the family". A shared one is seen and changed by every adult in the household; a shared bill is split equally or by income. When a member adds one, the app asks once whether it is shared, shared being the default inside a household.

**Demonstrated by:** Add the 3 000 zł flat as a shared bill split by income on your phone; on your wife's phone Plan shows it, she changes it to 3 100, and your Plan follows.

- **F12.8.1** Shared or mine on incomes, bills and the budget — A household scope on regular incomes, regular bills, one-off incomes and the household budget, readable and writable by every adult member (not by a child, F12.10); a split (equal or by income) on shared bills; the household month counts shared ones once. Domain model and ADR-0017 updated; cross-household and child-cannot-write tests (N2).
- **F12.8.2** Whose it is, on Plan and Settings — "Shared with family / Only mine" when adding or changing one (canvas F_Shared), a chip on every row (Shared, Mine, the member's name), who added it, and the split with each one's part. Checked at 375, 768 and 1280 px.

### F12.9 — The family's month on Home

*Requirements: —* · *Blocked by: F12.8*

Switching Home to the family still shows the first design. The family's month in the new one (canvas F_Home): what is left together, the shared income, bills and budget, and who spends what — each member's share in percent, as a ring, by category or by day — with others' private receipts as one undated sum (ADR-0017).

**Demonstrated by:** Switch Home to Family: the ring says what is left together; "Who spends what" shows you 62 % and Anna 38 %; tap Categories, then By day.

- **F12.9.1** Family Home in the new design — The household month and statistics endpoints extended with each member's share overall and per category; Home's Family view rebuilt after canvas F_Home with the chart switch (share, categories, by day). Checked at 375, 768 and 1280 px.

### F12.10 — Adults and children

*Requirements: N2* · *Blocked by: F12.8*

A family is not only two adults. A member is an adult or a child: a child adds their receipts and sees the family's month but changes nothing shared. The owner is an adult who also invites and removes people; whether only the owner may change the shared budget is the owner's choice.

**Demonstrated by:** Mark Max as a child: on his phone he adds a receipt, but the flat and the budget open read-only.

- **F12.10.1** Roles and what each may do — A role on the membership (adult, child), set by the owner (canvas F_Members); every shared write refuses a child; "only the owner changes the budget" setting; access tests for each role. Checked at 375, 768 and 1280 px.

### F12.11 — What the family buys, line by line

*Requirements: —* · *Blocked by: F12.9, F16.1*

What no bank-fed budget can show, because it never sees a receipt's lines: who buys what, products the family bought twice the same day or week, what on one receipt is the family's and what is one person's, and a family goal's advice naming the products to change.

**Demonstrated by:** Home shows "Bought twice this week: bread and milk, you both, on Tuesday"; a family goal "save 500 a month" lists the swaps that make it, by product.

- **F12.11.1** Who buys what and bought twice — Per member per product over a period from shared receipts only (ADR-0017), the same product bought by two members within a few days, and a card for it on the family Home. Checked at 375, 768 and 1280 px.
- **F12.11.2** Family goal advice by product — The goal check (F23.13) over the household's shared lines, naming products and the member-neutral swaps that reach the goal, from the family's own prices.

---

## E13 — Aggregated Purchase Analytics

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

After E21, and only if the diploma's timetable leaves room. The item-level data BO-2 produces is something bank and card feeds structurally cannot supply: what was actually bought, not which shop was paid. Aggregated across many users and anonymised, it first serves the users themselves — what a product costs across everyone and where it is cheapest this week — and could later be a saleable market signal (F13.6 and E18 decide whether, with a lawyer; nothing in this epic sells anything). The failure mode is legal rather than technical, so the constraints come first: no aggregate without explicit, revocable opt-in, no figure for a cohort small enough to identify someone, no row with a user in it ever leaving PostgreSQL. The warehouse is BigQuery within its free tier, filled by a job run from the backend's image as a Cloud Run Job — recorded as the first part to move into a service of its own when there are the means to run one.

### F13.1 — Explicit opt-in consent and withdrawal

*Requirements: N6* · *Blocked by: F17.9*

A separate, freely revocable consent — never bundled into terms of service and never a pre-ticked box — recording what was agreed to and when. Nothing else in this epic may touch a user's data without it, and withdrawal takes effect without the user having to ask twice. The privacy policy, terms and record of processing (ADR-0020) say so.

**Demonstrated by:** Turn on "Take part in shared price statistics" on Profile and read what it shares; open the privacy policy and find the new section and version; turn it off again.

- **F13.1.1** The sharing choice — A flag on the user with the time it was last changed, false for every account, existing ones included; a Profile switch saying what is shared — what was bought, where, for how much, by which week, never who — and that turning it off removes the user's part from the next recalculation, in three languages; the choice in the full data export (F17.9.2). Checked at 375, 768 and 1280 px.
- **F13.1.2** Privacy policy, terms and record of processing updated — ADR-0020 lists the aggregates, their purpose and legal basis (consent), the warehouse and its location, the minimum cohort, and that aggregates are not personal data once published; the /privacy and /terms pages say the same in three languages under a new TERMS_VERSION, and signed-in users are shown once that the policy changed. Checked at 375, 768 and 1280 px.

### F13.2 — Product normalisation catalogue

*Requirements: —* · *Blocked by: F16.1*

"MLEKO UHT 3,2% 1L" and "Mleko 3.2% 1l" have to become one canonical product across users, as F16.1 already makes them one within a user. This is the technical core of the epic: without normalisation the aggregates are noise, and normalisation quality sets the ceiling on what the data is worth. The catalogue holds names and sizes only, nothing of anyone's.

**Demonstrated by:** Two test accounts each buy "MLEKO 2% 1L" in different shops; both products point to one catalogue entry "mleko 2% 1 l".

- **F13.2.1** Shared catalogue and matching — A catalogue table keyed like a product — words and size, without the user — each user's product linked to one entry, matched by rule and, where unsure, by the model as F16.1 matches lines; filled as products are matched and for those already there; a merge or split (F16.1) moves the link; tests that no user id or receipt reaches the catalogue.

### F13.3 — Anonymisation and aggregation pipeline

*Requirements: —* · *Blocked by: F13.1, F13.2*

Pseudonymisation, deliberate coarsening of anything that narrows a person down, and aggregation — producing output in which no basket can be traced back to a household: weekly price aggregates per catalogue entry and shop chain (median, lowest and highest unit price, how many bought), from the purchases of users who opted in, recalculated from scratch every night.

**Demonstrated by:** Run the job on seeded data with twelve sharing accounts and read this week's price of "mleko 2% 1 l" in Biedronka from twelve contributors.

- **F13.3.1** Aggregation job — The weekly aggregates computed by the backend's image, runnable as a Cloud Run Job; no timestamps finer than the week, no addresses finer than the shop chain, no user ids in the output; unit prices per kg, l or piece as F16.2 compares them.

### F13.4 — Minimum cohort thresholds

*Requirements: —* · *Blocked by: F13.3*

No figure is published for a cohort below a defined number of contributing users. A query that would breach the threshold returns nothing rather than a small-sample number, because a small sample is how anonymised data stops being anonymous.

**Demonstrated by:** With nine sharing accounts buying a product, no aggregate for it exists; a tenth makes it appear on the next run.

- **F13.4.1** The contributor threshold — A setting, 10 by default, applied before anything is written; tests that an aggregate under it is never written, by the job or by any query.

### F13.5 — Separate analytics store

*Requirements: —* · *Blocked by: F13.4, F0.9*

Aggregates live outside the operational database, with no path from a business query back to a user's receipts. A boundary enforced by topology is worth more here than one enforced by review. The store is BigQuery in us-central1 within its free tier; the aggregates are also copied back into a PostgreSQL table the product screens read.

**Demonstrated by:** After a run, the BigQuery table holds the week's aggregates and nothing with a user in it; the service account that writes it can write nothing else.

- **F13.5.1** Warehouse in Terraform — A BigQuery dataset and table, the job and its nightly Cloud Scheduler trigger, a service account allowed to write only there; an ADR for the warehouse, the threshold and why the job is not yet a service of its own; docs/architecture/overview.md updated.

### F13.6 — Business insight API

*Requirements: —* · *Scope: Out of scope, unlike its epic*

Price and basket trends per product and category for business consumers, versioned and metered, delivering only what the aggregation pipeline has already cleared. Waits for an audience large enough to make the aggregates worth anything and for E18's legal work.

### F13.7 — Transparency and deletion propagation

*Requirements: N3, N6* · *Blocked by: F13.3*

A user can see what their data contributes, and withdrawing consent or deleting an account removes their contribution from future aggregates — the extension of N3 and N6 into a second data store. Recalculating from scratch each night is what makes it so: nothing of a user who stopped sharing survives the next run.

**Demonstrated by:** Turn sharing off for three of twelve contributing accounts and run the job again: the aggregate falls under the threshold and is gone from both stores.

- **F13.7.1** Withdrawal and deletion reach the warehouse — Tests that a user who stopped sharing or deleted the account is in no aggregate after the next run; Profile says how many of the week's published prices the user's purchases are part of. Checked at 375, 768 and 1280 px.

### F13.8 — Prices from everyone

*Requirements: —* · *Blocked by: F13.5, F16.3*

A product's page shows what it costs across everyone this week and where it is cheapest, beside what the user paid — for any product with enough contributors, and for any user, sharing or not: the aggregates are anonymous. The cheaper-shop hint (F16.3) uses them where the user's own receipts are too few.

**Demonstrated by:** Open "mleko 2% 1 l": "Everyone this week: median 3.49 PLN, cheapest at Lidl (2.99)", next to the user's own last price.

- **F13.8.1** Shared prices on the products screens — The week's aggregate for each product with a catalogue entry in the products API; the explore panel and the cheaper-shop hint showing it, in three languages, and saying nothing where no aggregate is published. Checked at 375, 768 and 1280 px.

---

## E14 — B2B Export & Accounting Integrations

**BRD sections:** — · **Phase:** 2 · **Scope:** Out of scope

Willingness to pay for structured receipt data is far higher among small businesses and the accountants who serve them than among individuals tracking groceries, and the sale needs no consumer marketing budget. F7.6 already exports CSV and JSON; this epic is about an export a bookkeeper's software ingests without a human reshaping it, the business fields such an export requires, and the extraction pipeline itself sold as an API.

### F14.1 — Business expense fields

*Requirements: —*

VAT rate and amount per line item, the merchant's tax identifier, and a business-or-personal split. BRD section 9's data model carries none of them, and an accounting export is worthless without all three.

### F14.2 — Accounting-format export

*Requirements: N6*

Export in the formats accounting software reads directly, rather than the generic CSV/JSON of F7.6 that leaves the reshaping work to whoever receives it.

### F14.3 — Scheduled and bulk delivery

*Requirements: —*

The monthly export is produced and delivered without anyone remembering to request it, including histories large enough that generating one synchronously is not an option.

### F14.4 — Receipt parsing API for third parties

*Requirements: —*

The extraction pipeline built in E3 offered as a product in its own right: API keys, a versioned response contract that callers can depend on across parser versions, and quotas.

### F14.5 — Usage metering and plan limits

*Requirements: —*

Counting what each account consumes — receipts parsed, API calls made, images stored. Every paid tier depends on this number, and nothing in phase 1 records it.

### F14.6 — Business account interface

*Requirements: —*

Export configuration, API key management and current usage against plan limits.

### F14.7 — Sole traders and KSeF invoices

*Requirements: —*

A Polish sole trader (JDG) keeps the firm's costs apart from the household's: purchase invoices fetched from KSeF, the national e-invoice system mandatory from 2026, with the trader's NIP and authorisation token; receipts and invoices marked as a business cost; VAT and the cost column of the revenue and expense ledger (KPiR) worked out per document; a month's costs handed to the accountant or sent to iFirma, inFakt or wFirma. The personal budget never counts a business cost, as business trips already are not.

### F14.8 — Tax deductions from receipts

*Requirements: —*

Purchases that lower personal income tax — medical and rehabilitation costs (ulga rehabilitacyjna), internet, thermal modernisation — recognised from receipt lines and gathered for the yearly PIT return, with the receipts that prove them kept past the usual 90 days.

---

## E15 — Receipt Accuracy & Trust

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

Reading a receipt is right on clean paper and wrong on a long, faded one with a dozen discounts: the best readers manage 70-85% there, and the apps on the market either hide the error or leave the user to find it. A receipt that does not add up and does not say why is the fastest way to lose a user's trust, and an untrusted figure makes every piece of advice built on it worthless. This epic makes every disagreement visible, explained and fixable in one step, marks the lines the reader doubted, remembers what the user corrected, and measures how often reading goes wrong.

### F15.1 — Explained totals mismatch and the missed-discount fix

*Requirements: —* · *Blocked by: F3.4, F3.9*

A receipt whose lines disagree with its printed total says by how much and why, wherever it is shown. Lines above the total usually mean a discount the reader missed, offered as one line of exactly that amount; lines below it mean a line is missing or misread. A grosz of rounding is not a disagreement. Nothing is added without the user's say.

**Demonstrated by:** Upload a Biedronka receipt whose OPUST lines were not read; the card says the lines come to 38.24 more than the 188.02 printed and offers a -38.24 discount; one click and the receipt adds up and counts toward the month.

- **F15.1.1** Missed discount added to an extracted receipt — Endpoint that appends one discount line to an extraction, filed under the receipt's dominant category, and re-checks its arithmetic; the same category for a discount typed into a stored receipt. One grosz of tolerance shared by upload and edit.
- **F15.1.2** Mismatch note in the upload wizard, the receipt view and the edit dialog — One shared note that names both figures and the gap, offers the discount when the lines are above the total and a way to fix the receipt when they are below.

### F15.2 — Doubtful lines marked

*Requirements: A10* · *Blocked by: F3.3, F15.1*

The lines the reader was unsure of are marked where the user looks at the receipt, with the photo beside them, so checking a receipt means checking three lines, not thirty.

**Demonstrated by:** Open a receipt read from a faded photo; two lines carry a "check this" mark, and the filter "doubtful only" shows just those two next to the photo.

- **F15.2.1** Keep each line's read confidence with the stored receipt — Persist the per-line extraction confidence on line items and return it with the receipt detail, so the mark survives storing the receipt.
- **F15.2.2** Doubtful-line marks and filter — Mark low-confidence lines in the upload wizard and the receipt view, with a filter showing only those and the receipt photo beside them.

### F15.3 — Corrections that stick

*Requirements: —* · *Blocked by: F15.1, F5.5*

A line name the user corrected on a receipt from one shop is corrected the same way on the next receipt from that shop, so the same misreading is fixed once, not every week.

**Demonstrated by:** Correct "MastoZPolskMlecz200g" to "Masło 200g" on one Biedronka receipt; the next Biedronka receipt reads "Masło 200g" and says it was corrected from what was printed.

- **F15.3.1** Per-shop correction memory applied at extraction — Record name corrections per user and merchant and apply them to later extractions from that merchant, keeping what was read alongside what is shown.
- **F15.3.2** Corrected-line indicator with undo — Show that a line was corrected from memory and let the user undo it for that line or forget the correction.

### F15.4 — Reading accuracy report

*Requirements: —* · *Blocked by: F15.2*

How often reading needs correcting, by shop and over time, measured from what users actually changed. It shows whether the trust work is working, and gives the diploma defence a number rather than a claim.

**Demonstrated by:** Open the accuracy panel and read that 4 of the last 20 receipts needed a correction, all from one shop, and that the share fell after corrections began to stick.

- **F15.4.1** Accuracy figures from corrections — Count receipts and lines changed after reading, per merchant and per month, from the stored corrections and mismatch fixes.
- **F15.4.2** Accuracy panel — A panel in Preferences showing the share of receipts corrected, the shops behind them and the trend.

### F15.5 — Receipts from any country, read right

*Requirements: A9, A10, A11* · *Blocked by: F3.4*

The reader was written for Polish receipts: its rules named OPUST, SUMA PLN and kaucja, and a Ukrainian receipt failed on its first discount, its rounding line and a McDonald's menu whose priced add-on was folded into the meal. The product is for Europe, so reading starts from rules that hold on any receipt — a discount is its own negative line, a footer sum of discounts or a payment is no line, a menu's unpriced parts are not lines but a priced add-on is — and adds short notes per country and, where a chain prints its own way, per shop. The model also gets a fixed budget to think before it answers, the photo is turned upright and made legible first, and a set of receipts with their right answers measures every change, so an improvement is a number rather than an impression.

**Demonstrated by:** Read the Sushizoom, McDonald's and Biedronka receipts of the evaluation set: every line, discount and total right, and the script reports the share of lines read right before and after.

- **F15.5.1** Reading rules for any receipt, with notes per country and per shop — One table of conventions (app/domain/receipt_conventions.py): general rules every receipt follows, then per country (PL, UA, DE, CZ, SK, AT, FR, NL, DK, SE, CH and more by adding a row) the words for discount, deposit, rounding, subtotal, amount to pay, payment and VAT marks, then per chain what it prints differently. The prompt is built from it, the reconciliation rules take their words from it, so a country added once is understood by both. Parser version bumped.
- **F15.5.2** A fixed thinking budget for reading — Reading with thinking switched off made the model transcribe without checking itself. Give it a fixed budget (Gemini thinkingBudget through LiteLLM) and raise the token limit by as much, so thoughts can never cut the JSON off; local models keep their own setting.
- **F15.5.3** Photos made legible before reading — Turn the photo upright from its EXIF orientation, trim plain margins, make it grey and stretch its contrast for faded thermal paper, and keep it within the size the model reads at full detail. A photo that cannot be processed is sent as it was.
- **F15.5.4** An evaluation set and score — Receipts with their right lines and totals, from the repository's own fixtures and receipts their owners agreed to share, and a script that reads each with the configured model and reports lines right, totals that agree and the time and tokens spent — run before and after a reading change.

### F15.6 — Lines added and removed, the total follows

*Requirements: A9, A11* · *Blocked by: F3.9*

A misread receipt is fixed line by line: a line the reader made up is removed, one it missed is added, and the receipt's total follows — removing 5 rolls at 10 takes 50 off it, removing a line read at 0 takes nothing. In the upload wizard and on a stored receipt alike, so what the receipt adds up to is always what its lines say.

**Demonstrated by:** Open a stored receipt with a line read twice, remove one: the total drops by its amount; add a missed line: it rises by that.

- **F15.6.1** Removing and adding lines with the total following — Remove and add a line in the upload wizard and in the stored receipt's edit dialog; the total changes by the line's amount; both through the services that keep a receipt's lines and total in agreement. Checked at 375, 768 and 1280 px.

---

## E16 — Personal Price History

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

Every receipt holds unit prices, and no app on the market uses them for the person who paid: banks never see a price, and receipt scanners stop at totals per category. The user's own receipts are enough to show how the price of what they buy is moving and where they pay less for the same thing, and those are the most concrete savings advice can name. This is personal, from one user's receipts only; aggregating across users is E13 and stays out of scope.

### F16.1 — One product across receipts

*Requirements: —* · *Blocked by: F3.5, F5.2*

The same product printed differently on different receipts and shops ("Jogurt Natural 330ml", "JOG NAT 330ML") is one product for that user, with a way to merge or split what was matched wrongly. Price history means nothing without it.

**Demonstrated by:** Open the products list and see one "Jogurt naturalny 330 ml" bought 9 times across two shops; merge in a line the matcher missed and split one it got wrong.

- **F16.1.1** Product model and matcher — A per-user product entity, line items linked to it, and a matcher that normalises names, sizes and units, behind a port so a model can help with ambiguous names.
- **F16.1.2** Products list with merge and split — A products screen listing what the user buys, with merge and split of wrongly matched lines.

### F16.2 — Exploring what I buy

*Requirements: —* · *Blocked by: F16.1*

The user picks one product or several ("chips and croutons") and a period, and sees how often they bought them, how much — in pieces, or kilograms and litres where the receipt gives a size — what it cost, and how that went month by month; for each product, what it cost in each shop and how much more one shop charged than another; and for one product, how its price moved. A selection can be saved under a name and opened again. Only the user's own receipts (N2). Lives as a "Products" tab beside categories on Statistics.

**Demonstrated by:** Pick "Chipsy Lay's 140 g" and "Sucharki 150 g", this month: bought 7 times, 0.98 kg, 41.30 PLN, more than last month; Lay's cost 6.99 at Biedronka and 8.49 at Żabka, 1.50 (21%) more; save the selection as "Snacks" and open it next month.

- **F16.2.1** Purchases of a selection over a period — Endpoint taking product ids and a period (whole days, inclusive, ADR-0012): times bought, quantity in pieces and in kg/l where known (never adding pieces to kilograms), amount spent, and the same per calendar month; for each product, each purchase's unit price (per kg/l where known) with its shop and date, and the change over the period. The caller's own receipts only, with a cross-user test (N2).
- **F16.2.2** Price per shop — For each selected product bought in more than one shop within the period: its average and latest unit price per shop, the cheapest shop, and how much more each other shop charged, absolute and in percent. Shops grouped ignoring case and spacing. Products of different sizes are compared per kg/l, or not at all when no size is known.
- **F16.2.3** Saved selections — Save a selection of products under a name per user, rename it, delete it; a product merged or split later (F16.1) keeps the selection pointing at what the user meant. Cross-user test (N2).
- **F16.2.4** Products tab on Statistics — A "Products" tab beside categories on Statistics: search products by name, tick one or several, pick the period with the existing period control; totals, month-by-month bars, a price-per-shop table and, for one product, the unit-price chart coloured by shop with the change stated in words. Saved selections one tap away. Checked at 375, 768 and 1280 px; on a phone the shop table becomes stacked rows.

### F16.3 — Where it costs less

*Requirements: —* · *Blocked by: F16.2*

Without the user asking, products bought in more than one shop say where the user recently paid less and by how much, only from their own receipts and only when both prices are recent enough to compare.

**Demonstrated by:** The products list says "cheaper at Lidl" next to five products, with the difference per unit, and none for a product last bought at Lidl a year ago.

- **F16.3.1** Cheaper shop for every product — Using the price-per-shop comparison of F16.2.2, find the cheaper shop for each of the user's products, counting only prices within a freshness window, and report the difference per unit.
- **F16.3.2** Cheaper-shop marks — Mark products with a cheaper shop in the products list and in the Products tab.

### F16.4 — Price signals in advice

*Requirements: F2, F4* · *Blocked by: F16.3, F8.5*

Price rises and cheaper shops become evidence advice can cite, so a recommendation can say "buy it at Lidl" with a saving computed from the user's own prices, not asserted.

**Demonstrated by:** Ask for advice on a spending ceiling and read "Buy Jogurt naturalny at Lidl: 0.80 less each, about 7 PLN a month at your rate".

- **F16.4.1** Price evidence in goal analysis — Add price rises and cheaper shops for the goal's products to the analysis the advice model reads.
- **F16.4.2** Saving from a shop switch — Compute the monthly saving of buying a product in the cheaper shop from the price gap and the user's purchase rate, the same way projected impact is computed for F8.5.

---

## E17 — Landing, Search and Analytics

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

The product has no public face and no way to tell whether anyone comes: the only page before signing in is a short welcome under a hosting address nobody remembers, search engines cannot read a client-rendered app, and nothing counts visitors, sign-ups or who stays. This epic gives the service a memorable free address and a landing page that explains it, makes accounts trustworthy and the user's data rights real (F17.8, F17.9) before anyone is invited in, then measures traffic and use without cookies — before anything is done to bring visitors, so each later step can be judged by its effect — adds an interactive demo on sample data and short how-to videos, makes it findable by search engines, and publishes the privacy policy, terms and cookie consent. Nothing here is bought: a domain and advertising wait for traffic (E19).

### F17.1 — A name worth remembering

*Requirements: —* · *Blocked by: F0.9*

The service is served at budget-agent.web.app instead of the project-derived hosting address, for free. A Firebase site name cannot change, so a new site is created and the old address redirects to it, path and query kept; everything that names the address — CORS, links, documentation — follows.

**Demonstrated by:** Open budget-agent.web.app and sign in; open the old address with a path and land on the same page at the new one.

- **F17.1.1** New hosting site with a redirect from the old one — A second Firebase Hosting site in Terraform as the one deployed to, the old site kept serving only a permanent redirect, the Deploy workflow and FIREBASE_SITE_ID switched, CORS and deployment documentation updated. Fails safe if the name is already taken by another project.

### F17.2 — Landing page that explains the product

*Requirements: —* · *Blocked by: F9.9, F17.1, F20.3, F20.5*

A visitor learns in one screen what the service does — receipts read from a photo, spending by category and product, goals with advice from their own purchases, households, trips — a holiday's budget, a business trip settled with its per diem — and finds the way to try it or sign up. Served as prerendered HTML, so search engines and link previews see the content without running the app; in English, Ukrainian and Polish.

**Demonstrated by:** Open the site logged out on a phone: a hero with the promise and a "Try the demo" button, sections per feature with real screens, a short FAQ, and the same page in Ukrainian and Polish at their own addresses.

- **F17.2.1** Landing content and design — Sections for the main features with screens from the product, a FAQ and calls to action, written in all three languages through the locales, designed against docs/design and checked at 375, 768 and 1280 px.
- **F17.2.2** Prerendered public pages per language — Build the landing and the other public pages as static HTML at build time, one address per language, so they render without JavaScript; the app takes over after load. Lighthouse performance and accessibility at least 90 on a phone.

### F17.3 — Knowing who comes and who stays

*Requirements: —* · *Blocked by: F17.2, F17.8, F17.9*

The author can see whether the service has an audience, from analytics of its own rather than a third party's: visitors to the public pages and where they come from, counted without cookies or any identifier, so no consent is needed and no other origin's script loads (F17.7.2); and for signed-in users, a record of what they do — signing up, confirming the address, signing in, uploading and reading receipts, exporting — kept 12 months for running and supporting the service (legitimate interest, art. 6(1)(f)), never the content of a receipt. Read on a dashboard for admins: sign-ups, confirmations, active users by week and month, who returns, the path from visit to first receipt.

**Demonstrated by:** Open the admin dashboard and read last week's visits to the landing page by source, 3 sign-ups of which 2 confirmed, 2 users active this week, 1 returning from last week, 14 receipts uploaded and 12 read.

- **F17.3.1** What signed-in users do — An activity table — user, event, when, and nothing more — written for signing up, confirming the address, signing in, uploading a receipt, a receipt read and an export; owned by the user, so the full export (F17.9.2) carries it and account deletion removes it; events older than 12 months pruned daily; ADR-0020 and the privacy policy saying what is recorded, why and for how long.
- **F17.3.2** Visits to the public pages without an identifier — The public pages tell the API "a view of this page, from this source" (referrer domain, utm_source) — no IP kept, no cookie, nothing stored on the device — counted per day, page and source; rate-limited, bots by user agent left out; a test that nothing identifying a visitor is stored, and lint:privacy still passing.
- **F17.3.3** Metrics dashboard for admins — An admin-only endpoint and page: visits by page and source, sign-ups and confirmations per day, weekly and monthly active users, returning users, receipts uploaded and read, and the path from visit to first receipt, over a chosen period; refused to anyone but an admin, with a test. Checked at 375, 768 and 1280 px.
- **F17.3.4** Where visits come from, by platform and system — Each counted view also says what it was opened in — the website, the iOS app or the Android app — and the operating system's family (iOS, Android, Windows, macOS, Linux, other), read from the User-Agent on the server and kept only as that word, never the header itself; the referring site and campaign as today. No cookie, no identifier, nothing more on the device (ePrivacy, ADR-0020). The admin metrics show views by source, platform and system over the chosen period. Tests that nothing but the counts is stored; checked at 375, 768 and 1280 px.

### F17.4 — Interactive demo on sample data

*Requirements: —* · *Blocked by: F17.2, F16.2*

A visitor clicks through the real screens — month, categories, products and prices, a goal with its advice — filled with a realistic sample household, without an account and without a single model call, and is invited to sign up from it. Nothing a visitor does in the demo is stored or reaches another user's data.

**Demonstrated by:** Press "Try the demo" on the landing page: the dashboard opens on a sample month with a "This is a demo" banner; open products, compare a price between shops, open a goal's advice; nothing can be uploaded or saved, and "Create an account" is one tap away.

- **F17.4.1** Sample data and a read-only demo session — A fixed sample account built from anonymised receipts, reachable through a short-lived read-only demo session that refuses every write and every model call, rate limited per client. Tests that the demo can neither write nor read real users' data (N2).
- **F17.4.2** Demo mode in the app — Entering the demo from the landing page, a banner saying it is a demo, writes disabled with a reason, and sign-up offered from it. Checked at 375, 768 and 1280 px.

### F17.5 — How-to videos

*Requirements: —* · *Blocked by: F17.4*

Short videos show the main flows on the real app with the sample data — photographing a receipt, fixing a doubtful line, watching a product's price, setting a goal — with captions in each language, recorded by script so they can be made again when the screens change.

**Demonstrated by:** Play "Upload a receipt" on the landing page: 30 seconds from the photo to the month, captioned in the page's language, without loading anything until played.

- **F17.5.1** Scripted recordings of the main flows — Browser-automation scripts that drive the demo and record each flow at phone and desktop size; captions per language; output small enough for the landing page.
- **F17.5.2** Videos on the landing page — Embed the videos with a poster image, loaded only when played, with captions and a text alternative.

### F17.6 — Found by search engines

*Requirements: —* · *Blocked by: F17.3*

Search engines can find, read and present the service: they are told what to crawl and what not to, the public pages carry titles, descriptions and previews, each language is linked to the others, and the site is registered with Google Search Console as a URL-prefix property, which a web.app address allows. The signed-in app is never indexed. Comes after analytics, so the effect of being indexed can be measured.

**Demonstrated by:** Search Console shows the landing page in three languages indexed with no coverage errors; sharing the link in a messenger shows the title, description and image.

- **F17.6.1** robots.txt, sitemap and page metadata — robots.txt allowing the public pages and excluding the app and the API, a sitemap.xml of the public pages per language, titles, descriptions, canonical and hreflang links, Open Graph and Twitter cards, and SoftwareApplication structured data; Lighthouse SEO at least 90.
- **F17.6.2** Search Console verification — Verify budget-agent.web.app in Google Search Console as a URL-prefix property through an HTML file or meta tag, submit the sitemap, and document how to read its reports.

### F17.7 — Privacy policy, terms and cookie consent

*Requirements: —* · *Blocked by: F17.2*

The service states what it collects and why and the terms it is offered under, in all three languages, linked from every public page and from sign-up. The website keeps on the device only what is strictly needed — the session, and choices the user made (theme, language, a list's period) — and loads nothing from third parties, so under ePrivacy it asks no consent, and a consent banner with nothing to ask would only train people to click through. A check in CI keeps it so: the day anything needing consent arrives, the build fails until it comes with its banner — on the website with AdSense (F19.3), in the app through Google's UMP (F19.4.1). Analytics (F17.3) stays cookieless and needs none. Wording to be checked against the E18 legal investigation.

**Demonstrated by:** Open the landing page on a phone: no banner, no cookie set; "Privacy" in the footer opens the policy in the page's language, which says what is kept on the device and why no consent is asked.

- **F17.7.1** Privacy policy and terms pages — The privacy policy and terms pages at /privacy and /terms, drafted in F17.9.4 from the record of processing (ADR-0020) and already linked from sign-up and Profile: their wording checked and completed (cookieless analytics, the consent choice), prerendered like the landing, and linked from the footer of every public page. Checked at 375, 768 and 1280 px.
- **F17.7.2** Nothing that needs consent, kept so by CI — A check run in CI that fails when the built site or the client's source loads a script, style, font or image from another origin, sets a cookie, or writes to the device's storage under a key not on the list of strictly needed ones; the list and why each entry is exempt in the privacy policy and ADR-0020. The consent banner itself moves to F19.3, where AdSense first needs it.

### F17.8 — Trusted accounts

*Requirements: —* · *Blocked by: F17.2*

An account belongs to a real address its owner can read: sign-up sends a link that confirms it, a forgotten password is reset and an address changed through a link sent to it, and throwaway or non-existent addresses are refused at sign-up. Until the address is confirmed the user may look around but not upload receipts, forward them by email or invite to a household. Mail goes out through App Engine's Mail API from noreply@<project>.appspotmail.com — free and needing no domain — behind a port, so a provider such as Resend replaces it once a domain is bought (E19); Google recommends moving off the legacy Mail API to SMTP providers, which the port makes a one-adapter change.

**Demonstrated by:** Sign up with a fresh address and find the confirmation letter; before following it the upload button explains why it waits; follow it and upload. Ask for a password reset and sign in with the new password. Try a mailinator address and a misspelt domain: both are refused with a reason.

- **F17.8.1** Outgoing email — An EmailSender port with an App Engine Mail adapter (the existing mail relay app, or a send endpoint beside it) and a stub for tests; letters in English, Ukrainian and Polish in the user's language; the daily quota checked in the project's console and recorded in an ADR with the fallback provider; sending failures logged and retried, never failing the request that caused them.
- **F17.8.2** Email confirmation — A confirmed flag on the user; a single-use signed link valid 24 hours sent on sign-up and on request, rate-limited; until confirmed, uploads, forwarded receipts and household invites are refused with a problem code the UI explains beside a banner offering to resend. Accounts created before this are marked confirmed by the migration. Checked at 375, 768 and 1280 px.
- **F17.8.3** Password reset and email change — Forgot-password sends a single-use link valid one hour, the same answer whether the address is known or not; setting a new password ends every session. Changing the address sends a link to the new one and only then switches it, telling the old one. Checked at 375, 768 and 1280 px.
- **F17.8.4** Refusing throwaway and undeliverable addresses — Sign-up and address change refuse domains on the open disposable-email-domains list, kept in the repository with a script that refreshes it, and domains without an MX (or A) record; each refusal with its own problem code and words in three languages. No third-party validation service: no address leaves the service at sign-up.

### F17.9 — Data rights and retention

*Requirements: N6* · *Blocked by: F17.2*

What GDPR requires before the service is offered to the public and before payments (E18): a user can take everything held about them and delete their account with all of it; receipt photos are kept 90 days — compressed when stored — and then deleted by the storage itself, while the figures read from them stay; export files are deleted after 7 days; the acceptance of the terms is recorded at sign-up; and what is processed, why, where and by whom — Google Cloud in the US, under the Data Privacy Framework and the Cloud DPA — is written down for the privacy policy (F17.7) to state. Replaces F10.7, which sat in an epic out of the diploma's scope.

**Demonstrated by:** Download everything from the profile and open the archive; delete the account, then fail to sign in and find no photo left in storage. Open a receipt older than 90 days: its lines and totals are there, and the photo is marked as removed after 90 days.

- **F17.9.1** Account deletion — Deleting the account, confirmed with the password, removes the user and everything theirs — receipts with their photos, trips, goals, advice, categories and rules, products, exports, upload jobs — and their place in a household: an owner leaving hands it to another member, the last one dissolves it. Sign-in fails afterwards; tests prove nothing of the user is left. Checked at 375, 768 and 1280 px.
- **F17.9.2** Full data export — One archive of everything held about the user — profile, receipts with lines, trips, goals and advice, categories and rules, products, household membership — as JSON, with the photos still kept, through the export jobs of F7.6. Checked at 375, 768 and 1280 px.
- **F17.9.3** Photo retention and compression — Bucket lifecycle rules in Terraform deleting receipts/ objects after 90 days and exports/ after 7; photos re-encoded on upload to about 2000 px JPEG after reading; a receipt whose photo is gone says so instead of a broken image, and a business trip warns before its photos expire. The settlement PDF is still produced after: the summary and totals unchanged, no page for a photo that is gone — no placeholder — and its receipt marked "photo removed after 90 days" in the list, as a typed-in expense is marked "no receipt"; with every photo gone it is the summary alone. Checked at 375, 768 and 1280 px.
- **F17.9.4** Terms acceptance and the record of processing — Sign-up requires accepting the terms and privacy policy, storing when and which version; an ADR listing the personal data held, its purpose, legal basis, storage location, retention and processors (Google Cloud, Vertex AI, Firebase), and the transfer to the US, for the privacy policy to rest on. Checked at 375, 768 and 1280 px.

### F17.10 — Help and contact

*Requirements: —* · *Blocked by: F17.2, F17.8*

A user with a question finds the answer without leaving the product, and when there is none, writes to the people running it. A help page answers the usual questions by area — receipts, categories, goals, the household, trips and per diem, exports, the account and its data — in all three languages, public and prerendered like the landing, linked from the header, the account menu and the footer. A contact form sends the message to the administrators by the outgoing mail of F17.8, so no address is published and no domain is needed.

**Demonstrated by:** Open Help from the account menu on a phone, find how a business trip's per diem is counted, then send a question through the form and see it arrive in the administrators' inbox with the sender's address to reply to.

- **F17.10.1** Help page — /help with questions and answers grouped by area, each answer linkable, in three languages through the locales, prerendered with the public pages, linked from the header, the account menu, the phone's profile menu and the footer. Checked at 375, 768 and 1280 px.
- **F17.10.2** Contact form — A form — reply address (filled in for a signed-in user), topic, message — whose submission is mailed to the administrators (admin_emails) through the EmailSender port, rate-limited per address and IP, with a honeypot field against bots and a length limit; the sender gets a copy confirming it was received. Checked at 375, 768 and 1280 px.

### F17.11 — The public site in the new design

*Requirements: —* · *Blocked by: F17.2, F17.10, F23.2*

The landing and Help still show the first design and the app as it was before E23: old screens, old paths (Profile, Categories, Receipts) and Polish shops and złoty on the front page. The product is for any country, so the public pages say nothing tied to one: amounts follow the visitor's language, shops are generic. The landing follows variant C of the design canvas — a large headline over three phones showing the real screens, "one total vs every line", three steps, a tabbed "see what you can do" over Home, Spending, Products and Plan, the features, a free card, questions and a closing call. Help becomes something to use, not to read through: a search, the app in four steps, topics that filter the answers, each answer saying where in the app the thing is, and the contact form beneath.

**Demonstrated by:** On a phone, open the landing, tap through Home, Spending, Products and Plan in "see what you can do", then open Help, search "rent" and follow the answer to Plan › Regular bills; switch the language to Polish and see both pages in it.

- **F17.11.1** Landing in the new design — The landing rebuilt after the canvas's "Landing C" (docs/design/v2.md): hero with three phones drawn with the app's own ring, colours and rows on sample data, "most apps see one total, Budget Agent sees every line", three steps, the tabbed Home / Spending / Products / Plan showcase, six feature cards, the free plan, the questions and the closing call, in the v2 tokens and palette. No country, shop or currency is named; sample amounts are formatted for the page's language. All text through the locales in en, uk and pl, still prerendered with its title, description and previews per language. Checked at 375, 768 and 1280 px.
- **F17.11.2** Help that is easy to use — /help rebuilt after the canvas's "Help" (docs/design/v2.md): a search over questions and answers, "the app in four steps" (add a receipt, check what was read, see where it went, plan the month), topic cards that filter the answers (receipts, spending, products, income and bills, goals, household, holidays and trips, account and data), answers rewritten for the app as it is now, each with where it lives ("Plan › Regular bills"), each still linkable, and the contact form of F17.10.2 beneath. Three languages, prerendered. Checked at 375, 768 and 1280 px.

---

## E18 — Subscriptions and Payments

**BRD sections:** — · **Phase:** 2 · **Scope:** Out of scope

Payments stay out of the diploma's scope, but plans (F18.2), what a plan gives (F18.4) and the admin console that grants them (F18.6) are in it. A free account reads ten receipts a month (and, once E19 brings them, sees ads). Paying raises the limit, and removes ads when there are any, priced from what a receipt read actually costs, so the service covers its model calls. The author sells through a Polish sole-proprietorship (JDG); how that may lawfully take card payments for a subscription — VAT on EU consumers, invoices and receipts, consumer withdrawal rights, the terms — is investigated before any code, and the payment provider is chosen from it. Payments run in the provider's test mode until the legal checklist is closed. Out of the diploma's scope while traffic is unproven: it needs paid services and legal work the author will not spend on before there are users.

### F18.1 — Selling a subscription as a Polish JDG

*Requirements: —*

What a JDG must have and do to sell a monthly subscription to consumers in Poland and the EU: where the money is paid out to, VAT for EU consumers (OSS) or a merchant of record taking it on, invoices and receipts (including whether a cash register is required for online payments, and KSeF), the consumer's right of withdrawal for a digital service, and what the terms must say. Answered with sources in an ADR and a checklist for the author's accountant; not legal advice.

**Demonstrated by:** Read the ADR: it recommends selling directly or through a merchant of record, lists what the JDG needs (business bank account, VAT registration status, documents), and the open points for the accountant.

- **F18.1.1** Legal and tax investigation — Research the questions above from official sources (podatki.gov.pl, EU OSS, UOKiK, the act on providing services electronically) and the providers' own terms; write the ADR with sources and the accountant checklist.
- **F18.1.2** Choose the payment provider — Compare a direct processor (Stripe) with merchants of record (Paddle, Lemon Squeezy) on fees, VAT handling, payout to a Polish account, JDG eligibility, Polish payment methods (BLIK, Przelewy24) and test mode; record the choice in an ADR.

### F18.2 — Plans and prices

*Requirements: —* · *Blocked by: F10.6* · *Scope: Diploma, unlike its epic*

Plans priced from what a receipt read costs: the free plan keeps its limit (and the ads E19 may bring); a paid plan raises the limit and is ad-free; a larger one raises it further. The figures — cost per read, limits, prices, margin — are worked out and recorded, and the plans live in configuration, not code.

**Demonstrated by:** Read the pricing ADR: cost per read from the model's measured tokens, three plans with limits and prices, and the margin at each.

- **F18.2.1** Cost per read and the plans — Measure tokens per receipt read and per advice call, cost them at the model's prices and the hosting costs, and set the plans' limits and prices in an ADR.
- **F18.2.2** Plans in configuration — Plans with their monthly receipt limit and ad-free flag in settings, replacing the single free limit: free (10 reads a month) and a paid plan (200), more added by configuration; the free plan unchanged for existing accounts.

### F18.3 — Paying for a subscription

*Requirements: —* · *Blocked by: F18.1, F18.2*

A user subscribes, changes plan or cancels through the provider's hosted checkout and customer portal — card details never touch the service — and the service learns of every change from the provider's signed webhooks, idempotently, so a retried or late event never double-charges or misstates a plan.

**Demonstrated by:** In test mode, choose the paid plan, pay with the provider's test card on its checkout page, return to the app with the plan active; cancel in the portal and see it end at the period's close.

- **F18.3.1** Checkout and customer portal — Endpoints creating a checkout session and a portal session for the signed-in user, behind a port so the provider can be swapped; test keys only in development and CI; secrets in Secret Manager.
- **F18.3.2** Signed webhooks and subscription state — A webhook endpoint verifying the provider's signature, storing each event once, and keeping the user's subscription — plan, status, period end — current; tests for replayed, out-of-order and forged events, and a cross-user test (N2).

### F18.4 — What a plan gives

*Requirements: —* · *Blocked by: F18.2* · *Scope: Diploma, unlike its epic*

The plan sets the month's receipt limit and whether ads may show (E19). Until payments exist (F18.3) a paid plan is one an admin granted for a time (F18.6); then a subscription gives it the same way. A plan that ends — a grant past its date, a cancelled subscription past its period — leaves the free plan.

**Demonstrated by:** Granted the paid plan for a month, the profile shows 200 receipts a month until the grant's end date; the day after, 10 again.

- **F18.4.1** Limits and ads from the plan — The receipt quota (F10.6) and an ad-free flag on the user read from the active plan, falling back to free at period end.
- **F18.4.2** Plan on the profile — The current plan, its limit and its end date on Profile, and the provider's portal link once payments exist (F18.3). Checked at 375, 768 and 1280 px.

### F18.5 — Pricing page

*Requirements: —* · *Blocked by: F18.2, F17.2*

A public page comparing the plans in each language, from the same configuration the service enforces, leading signed-out visitors to sign up and signed-in ones to checkout.

**Demonstrated by:** Open "Pricing" from the landing page on a phone: three plans side by side as stacked cards, the current plan marked when signed in.

- **F18.5.1** Plans comparison page — Public, prerendered pricing page per language from the plans endpoint, with calls to action by state. Checked at 375, 768 and 1280 px.

### F18.6 — Admin console

*Requirements: N2* · *Blocked by: F17.3, F18.2, F17.8* · *Scope: Diploma, unlike its epic*

Running the service without touching the database: super admins (the author and his wife, named in configuration) appoint and remove admins, and only they can; every admin signs in with a second factor, which any user may also turn on for their own account; admins find a user by address and see their account — whether confirmed, when they signed up and were last active, the month's reads, the plan and until when, recent activity — never their receipts (N2); and act for them: confirm the address, send the confirmation or a password reset link, grant a paid plan for a time or take it back. Every admin action is recorded, who did what to whom.

**Demonstrated by:** Sign in as a super admin with the authenticator code, make a user an admin, grant another the paid plan until next month and see it on their profile; read both actions in the admin log.

- **F18.6.1** Roles and two-factor sign-in — Super admins from configuration (admin_emails), admins as a role stored on the user, granted and removed only by a super admin; a TOTP second factor (authenticator app, set up by QR code, with 10 single-use recovery codes) that any user may turn on in Preferences and that every admin must have — an admin without it is asked to set it up before any admin page opens — switched off by a setting for local work; a letter to the admin on each admin sign-in; tests that an admin cannot appoint anyone and that a password alone never opens an admin session. Checked at 375, 768 and 1280 px.
- **F18.6.2** Users and support actions — The users list with search by address and filters (confirmed, plan, active), the user's card with account facts, usage and recent activity (F17.3.1) but nothing of their receipts, and the actions: confirm the address, resend the confirmation, send a password reset link (F17.8.3). Checked at 375, 768 and 1280 px.
- **F18.6.3** Granted plans and the admin log — Plan grants — user, plan, from, until, who granted, why — made, extended and taken back from the user's card, the active one setting the plan (F18.4); an admin log of every admin action, read by super admins; ADR-0020 listing the admin log. Checked at 375, 768 and 1280 px.

---

## E19 — Advertising

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

Advertising is how the free plan pays for itself. In the Android app (E22) it needs no domain: AdMob ties ads to the app in Google Play, with app-ads.txt on the web.app site the listing names. Free accounts see an unobtrusive banner, and once the month's ten receipt reads are used up, can watch a rewarded ad for one more — a view earns more than a read costs (about $0.005-0.02 against $0.001-0.005), and the user chooses it. Ads on the website still need a domain of the service's own (AdSense wants ads.txt at a domain's root), so F19.1 and F19.3 wait, out of the diploma's scope, for traffic. Taken on with E22, after F17.7, whose consent covers ads.

### F19.1 — The service's own domain

*Requirements: —* · *Blocked by: F17.3* · *Scope: Out of scope, unlike its epic*

Once traffic justifies it, the service moves to a domain of its own, bought by the author, with HTTPS and the API under the same name; budget-agent.web.app redirects to it.

**Demonstrated by:** Open the service at its own domain over HTTPS; the web.app address redirects to it.

- **F19.1.1** Domain on hosting and API, in Terraform — Point the domain at Firebase Hosting and the API at Cloud Run through Terraform, with managed certificates; redirect the web.app address; update CORS, Search Console (as a domain property) and the deployment documentation.

### F19.4 — Ads in the Android app

*Requirements: —* · *Blocked by: F22.2, F17.7*

AdMob in the app for accounts without an ad-free plan: one banner of reserved size at the foot of the dashboard and statistics, never in the upload flow, a dialog or a form, shown only after the EEA consent Google's UMP SDK asks for (personalised or not, as chosen). app-ads.txt is served from budget-agent.web.app, the site the Play listing names.

**Demonstrated by:** In the app on a free account, accept or refuse ad consent, then scroll the dashboard to its foot: one banner that did not shift the page; none on an admin account.

- **F19.4.1** AdMob account, app-ads.txt and consent — The AdMob account under the business, the app registered, app-ads.txt on Firebase Hosting, the UMP consent form in three languages with the choice changeable from Profile; the record of processing (ADR-0020) and /privacy updated for ads.
- **F19.4.2** Banner placements — Reserved-size banner slots in the app only (never on the web build), hidden for admins and ad-free plans, and a test that no slot appears in the upload flow or any dialog. Checked on a phone and a tablet.

### F19.5 — One more receipt for a rewarded ad

*Requirements: —* · *Blocked by: F19.4, F10.6*

When the month's receipt reads are used up, the upload screen offers "Watch a short ad for one more receipt" instead of only saying when the limit resets. The extra read is granted by the server only when AdMob's server-side verification callback confirms the ad was watched — signed by Google, checked against its public keys, each reward once — so it cannot be claimed by calling the API. A daily cap keeps it bounded.

**Demonstrated by:** On an account at its limit, press "Watch an ad for one more receipt", watch it, and upload a receipt; the quota shows the extra read was used.

- **F19.5.1** Verified rewards in the quota — A public SSV callback endpoint verifying Google's signature and refusing a transaction id seen before; earned reads stored per account and day and counted by the quota (F10.6) after the monthly ones; a daily cap as a setting; tests of a forged, replayed and over-cap reward.
- **F19.5.2** Rewarded ad on the upload screen — The offer at the limit in the app only, the rewarded ad loaded and shown, the quota re-read after the reward; what the web build says instead. Checked on a phone and a tablet.

### F19.3 — Advertising on the website

*Requirements: —* · *Blocked by: F19.1, F17.7* · *Scope: Out of scope, unlike its epic*

Google AdSense shows ads on the public pages and in one or two places in the app that never sit inside a task — never in the upload wizard, a dialog or a form — and only for accounts whose plan is not ad-free (F18.4). Ads respect consent, do not shift the layout as they load, and fit a phone.

**Demonstrated by:** Signed in on the free plan, scroll the dashboard to its foot and see one ad block that did not move the page as it loaded; on a paid account the block is not there.

- **F19.3.1** AdSense account, site approval and consent — Create the AdSense account for the business, add ads.txt at the domain's root, request site approval, and document the policies the placements must keep to; the consent banner moved here from F17.7.2 — a Google-certified consent platform with accept, reject and per-purpose choices in three languages and Consent Mode v2, no ad script before consent, the choice changeable from the privacy page.
- **F19.3.2** Ad placements — Reserved-size ad slots on the landing page and at the foot of the dashboard and statistics, loaded after consent, hidden for an ad-free plan, and a test that no slot appears in the upload wizard or any dialog. Checked at 375, 768 and 1280 px.

---

## E20 — Trips

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

A trip is spending with a shape of its own — a week in Egypt, a weekend in the mountains, a client visit in Berlin — that a month's total hides. A user marks a trip, and its receipts gather on it, foreign ones already converted at NBP rates (ADR-0016). A personal trip is the user's own money: it stays in the month, shown apart, with a budget of its own and what it cost by day and category. A business trip is the employer's money: it stays out of the personal budget, and the service works out the per diem owed under Polish rules and produces the settlement to hand in — the service's small step towards business use, without accounts for companies. One kind of record serves both; only how a trip counts and what comes with it differ.

### F20.1 — Trips and their receipts

*Requirements: —* · *Blocked by: F3.9, F11.7*

A user records a trip — personal or business, a name, where to (country and city), when it started and ended, and why — and its receipts gather on it: a personal trip takes those dated within it by itself, a business trip asks about each one first (a purchase on a business trip may be the user's own), any can be added or taken out by hand, receipts can be uploaded straight from the trip's page, and a run of foreign receipts on consecutive days prompts "was this a trip?". A personal trip's receipts stay in the month and its limit, marked as the trip's; a business trip's are the employer's money and stay out of the personal month, its limit, statistics, goals and advice, and the household's totals. The dashboard says how much went on trips, apart.

**Demonstrated by:** Create "Egypt, holiday, 1–8 Oct" as personal and "Berlin, client visit, 13–15 Oct" as business: October still counts the Egypt receipts, with "of which Egypt: 2 840.00 PLN" beside the total; the Berlin ones are out of it, shown as "Business trips, to be repaid: 612.40 PLN".

- **F20.1.1** Trips and receipt assignment — Trip entity per user with its kind (personal or business), destination, dates and purpose; receipts within a personal trip's dates joined automatically, those within a business trip's dates only asked about and counted in the user's budget until answered; manual add and remove that later automatic passes respect; the upload wizard's commit records the user's answer per receipt; one trip per receipt; the suggestion from consecutive foreign receipts. Endpoints for trips and their receipts, cross-user tests (N2).
- **F20.1.2** How a trip counts in the budget — Business trip receipts excluded from the month, its limit and snapshots, statistics, goal progress and advice, and the household's totals; personal trip receipts counted as before and marked with their trip; the month's summary carries both amounts apart. Tests for each, domain model updated.
- **F20.1.3** Trips screen and trip page — A trips list and a trip page with its receipts, creating and editing a trip of either kind, moving a receipt in or out from the receipt view, the suggestion as a dismissible note, and the dashboard's trip lines. The upload wizard asks about a receipt dated within a trip — a tick for a personal one, a required "the company's or mine?" for a business one — an upload started on a trip's page goes into it, a business trip's page asks about receipts that arrived by email, and the receipts list labels each receipt's trip. Checked at 375, 768 and 1280 px.

### F20.2 — What a trip cost, by kind

*Requirements: —* · *Blocked by: F20.1*

A trip's spending splits into transport, accommodation, meals and other — what a settlement asks for and what a holiday is remembered by — each receipt filed under one, guessed from its shop and lines and corrected by the user, with totals per kind in the account's currency and in each currency paid.

**Demonstrated by:** Open the Egypt trip: transport 1 900.00, accommodation 0.00 (all-inclusive), meals 310.00, other 630.00 PLN; the souvenirs paid in Egyptian pounds show their own amount beside the converted one; move a taxi receipt from "other" to "transport" and the totals follow.

- **F20.2.1** Expense kind per trip receipt — Each trip receipt filed under transport, accommodation, meals or other, guessed from the merchant and its categories behind a port, the user's choice kept over later guesses; totals per kind and per currency paid.
- **F20.2.2** Trip spending by kind on the trip page — Totals per kind and per currency, each receipt's kind changeable in place. Checked at 375, 768 and 1280 px.

### F20.3 — A personal trip's budget and story

*Requirements: —* · *Blocked by: F20.2*

A personal trip can have a budget of its own — "3 000 zł for the mountains" — and the trip page says how much of it is left, what each day cost and where the money went by category, during the trip and after it. The month it falls in still counts it; the trip page is where it is read as one story.

**Demonstrated by:** Give "Mountains, 10–12 Oct" a 3 000 PLN budget: day by day 1 120, 860 and 640 PLN, 380 PLN left, most of it on accommodation; the month's dashboard counts the 2 620 PLN and links to the trip.

- **F20.3.1** Trip budget and daily spending — An optional budget on a personal trip, what is left of it, spending per day of the trip and per category, from the trip's receipts only; the user's own trips (N2).
- **F20.3.2** Budget and days on the trip page — Setting the trip budget, a meter of it, the days and categories, and the link from the dashboard's trip line. Checked at 375, 768 and 1280 px.

### F20.4 — Per diem under Polish rules

*Requirements: —* · *Blocked by: F20.1*

For a business trip, the per diem an employer owes, as the Polish regulation on employees' business travel sets it: the domestic rate, or the destination country's rate in its currency for a trip abroad, by the hours away, reduced for meals that were provided — worked out from the departure and return times the user gives, never guessed, and showing how it was reached.

**Demonstrated by:** A business trip from 13 Oct 06:00 to 15 Oct 21:00 in Germany with two hotel breakfasts: the trip page shows the per diem in euros and in złoty, each day and each reduction itemised, with the regulation it follows named.

- **F20.4.1** Per diem rules and rates — Research the current regulation and its annex from official sources: the domestic rate, rates per country, how hours away become days and parts of days at home and abroad, meal reductions, and when the rate in force is read; an ADR with sources, and the rates in configuration with the date they apply from.
- **F20.4.2** Per diem calculation — A pure calculation from departure and return times, destination and meals provided, itemised per day, tested against the regulation's own worked cases; converted to złoty at the NBP rate the rules name; stored with the trip. Business trips only.
- **F20.4.3** Per diem on the trip page — Departure and return times and meals provided entered on a business trip, the per diem shown itemised with the rule behind each line. Checked at 375, 768 and 1280 px.

### F20.5 — Business trip settlement to hand in

*Requirements: N6* · *Blocked by: F20.2, F20.4, F7.6*

The settlement an employee gives the employer for a business trip: its details, spending by kind and currency, the per diem, any advance already received, and what remains to be paid back to them — as a PDF with every receipt's photo attached, and as CSV, in the user's language. An expense with no receipt — a tour paid in cash, a tip — can be typed in, anywhere a receipt can be added, and counts like one, marked as having no document.

**Demonstrated by:** Enter a 500 PLN advance on the Berlin trip and download the settlement: one PDF with the summary, "to reimburse 612.40 + 207.00 − 500.00 = 319.40 PLN", and the receipts' photos on the pages after.

- **F20.5.1** Settlement export — PDF and CSV of a business trip's settlement through the export jobs of F7.6, with the receipts' photos in the PDF, in the user's language; the advance stored on the trip; the user's own trips only (N2). An expense without a receipt stored as a one-line receipt of a `manual` channel — description, date, amount, currency, category, optional kind and trip — counted like any receipt, kept out of the reading-accuracy report, and marked in the settlement.
- **F20.5.2** Advance and download on the trip page — The advance received, the amount to reimburse, and the settlement download on a business trip; adding an expense without a receipt from the receipts list, the upload page and a trip's page, asked about a trip like the wizard asks. Checked at 375, 768 and 1280 px.

---

## E21 — Voice and Chat Assistant

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

After the Android app (E22) and its ads (E19), before E13. The agent the diploma is about, made something a user talks to: they say or type what they want — "I spent 45 zloty on a taxi yesterday", "how much did I spend on coffee in October?", "I want to save 3 000 for a holiday by June" — and the assistant answers in a chat, showing what it understood as a card. Nothing is written until the user presses Save on the card; a question is answered at once, since it changes nothing. It grows step by step until everything a user can create or look up on the screens can be done by voice — expenses, receipts, balances, goals, questions about spending, products and prices, the settings and, for admins, the admin console — like a tool server (MCP) over the whole app: it sees everything the user has and acts through approved cards. Only signing in stays on the screens: password, email, the second factor and deleting the account (ADR-0029). The assistant acts only through the services the screens use, so ownership (N2), quotas and every rule hold as they do; conversations and their cards are kept like any other user data, exported and deleted with the account.

### F21.1 — Conversations and the chat screen

*Requirements: N2, N6* · *Blocked by: F17.9*

A chat screen, reachable from the navigation on every screen, where the user writes and the assistant answers; conversations kept and listed, newest first, each one reopened where it was left. A message is the user's text, the assistant's text, or a card — a proposed action with its fields and its state (proposed, saved, dismissed) and, once saved, a link to what it created. Every question and every card is a model call, counted against the account's quota like a receipt read.

**Demonstrated by:** Open the assistant, ask "what can you do?", close the app, open it again: the conversation is there and continues.

- **F21.1.1** Conversation and message storage — Conversation and message tables owned by the user (ON DELETE CASCADE, so account deletion and the full export of F17.9 take them with no extra code); a message's kind, text and card as JSON with its state; endpoints to list, open and continue a conversation; cross-user access tests (N2); rate limit and quota per message.
- **F21.1.2** Assistant port and the tool protocol — An AssistantPort behind the LiteLLM agent (ADR-0006) taking the conversation and a registry of tools, each a narrow function over an existing service: read tools run at once, write tools only return a proposed card. A stub for tests; an ADR on why writes go through user-approved cards and never straight from the model; docs/architecture/overview.md and ADR-0020 (conversations and transcripts as personal data, kept until deleted) updated.
- **F21.1.3** Chat screen — The chat: messages, cards rendered by kind with Save and Dismiss, the conversation list, a store owning it all; three languages. Checked at 375, 768 and 1280 px.

### F21.2 — Speaking to the assistant

*Requirements: —* · *Blocked by: F21.1*

A microphone button beside the text field: the user speaks in Ukrainian, Polish, English or Russian and the words appear as their message before the answer; saying "approve" saves the card waiting for it. The browser's own recognition (F21.2.1) proved too poor in use and was hidden on 2026-10-20; the speech is now recognised by Google Cloud Speech-to-Text (Chirp) behind our own port (F21.2.2, ADR-0031): the recording goes to the service, is recognised and is not kept. It costs about 0.016 USD a minute after the free minutes, bounded per user.

**Demonstrated by:** Tap the microphone and say "wczoraj taxi 45 złotych": the message appears, then the assistant's card.

- **F21.2.1** Speech to text in the browser — The Web Speech API in the user's language, words shown as they are heard and sent when the phrase ends, "approve" in three languages saving the waiting card, the microphone hidden where unsupported, and the privacy policy saying the browser's maker may recognise the sound. Checked at 375, 768 and 1280 px. Built, then hidden on 2026-10-20 and superseded by F21.2.2: the browser's recognition proved too poor; closed with F21.2.2's recogniser in place.
- **F21.2.2** Speech recognised by Google Cloud — The microphone records in the browser (MediaRecorder, at most 60 seconds, a second tap or silence ends it) and sends the sound to POST /api/v1/assistant/speech; a SpeechPort with a Speech-to-Text v2 adapter (Chirp 3, the language told by the sound) returns the text, which is put in the field to send or correct. Nothing of the sound is stored; seconds recognised per user per day bounded (rate limit), counted in the AI allowance once F21.9 lands. A stub port for tests and local work without Google credentials. Terraform enables the API and grants the runtime account the right to use it. The privacy policy says the recording goes to Google Cloud for recognition and is not kept; ADR-0031 replaces ADR-0025's speech bullet. Checked at 375, 768 and 1280 px.

### F21.3 — Expenses by voice

*Requirements: —* · *Blocked by: F21.2, F20.5*

The first thing the assistant does: "I spent 45 zloty on a taxi yesterday" becomes a card — description, amount, currency, date, category, trip if it falls in one — that the user corrects in place and saves as an expense without a receipt (F20.5), or dismisses. Several expenses in one sentence become several cards.

**Demonstrated by:** Say "yesterday taxi 45, coffee 12": two cards appear; change the coffee's category, press Save on both; both are on the receipts list and in the month's total.

- **F21.3.1** Expense tool and card — A write tool proposing manual expenses, dates resolved against the user's today and timezone, the category from the user's categories; the card's fields editable before Save; saving through the manual expense service, the card then linked to the receipt; tests that nothing is stored before Save and that another user's category or trip is never offered (N2). Checked at 375, 768 and 1280 px.

### F21.4 — Questions about spending

*Requirements: —* · *Blocked by: F21.1*

"How much did I spend on coffee in October?", "where do I buy milk cheapest?", "what did I spend in Lidl this month?" — answered from the same queries the statistics, receipts and products screens use, as text and, where a figure is clearer drawn, a small chart card, with a link to the screen that shows it in full.

**Demonstrated by:** Ask "how much did I spend on groceries this month compared to last?": the answer with both sums, the change, and a link to Statistics for those two months.

- **F21.4.1** Read tools over statistics, receipts and products — Read tools for category totals over a period, receipts by shop, text and period, and a product's prices and shops (F16.2-3); answers in the user's language and currency; tests that a tool only ever reads the caller's data (N2).
- **F21.4.2** Answer and chart cards — A chart card for totals over time or by category, and a link card to the screen with the same filters. Checked at 375, 768 and 1280 px.

### F21.5 — Goals by voice

*Requirements: —* · *Blocked by: F21.3, F8.11*

Adding, changing and removing a goal by chat came with F21.7. What is left is talking about a goal: "how am I doing with my holiday goal?" answered from its progress (F8.11), "I have these goals, what should I do with them?" answered with the advice the goals screen gives, and "tell me about my goal 'lose weight' — which products should I drop?" answered as a table of the bought lines the goal watches, with what each cost a month. Every goal call to the model is counted in the AI budget (F21.9).

**Demonstrated by:** Ask "which products should I drop for my lose-weight goal?": a table of the watched products with a month's cost each and a link to the goal on the Goals screen.

- **F21.5.1** Goal progress, advice and the products table in the chat — A read tool for one goal's progress (F8.11) and its current advice, a tool asking for fresh advice through the advice service (counted in the AI budget, F21.9), and a read tool listing the lines a goal watches over the last months with count and a month's cost, drawn as an answer card with a table and a link to /goals; tests that only the caller's goals are read (N2). Checked at 375, 768 and 1280 px.

### F21.6 — Receipts, trips and products by voice

*Requirements: —* · *Blocked by: F21.4, F21.5*

Everything the screens do with the user's purchases: find a receipt and show it, say which receipts wait for review and why (the review statuses of F15), correct a line — name, price, quantity, category — add or remove a line with the total following (F15.6), mark a receipt reviewed, delete a receipt, put it on a trip or take it off, start a trip, save a selection of products to watch. Each change is a card the user approves; the assistant says plainly what it cannot do and where on the screen it is.

**Demonstrated by:** Ask "what is waiting for review?": two receipts and why; say "on the Biedronka one the milk was 4.29": a card with the line; approve; the receipt total follows.

- **F21.6.1** Remaining write tools — Write tools for a receipt's trip, a line's category, a new trip and a product selection, each a card saved through its service. Checked at 375, 768 and 1280 px.
- **F21.6.2** Receipts found, reviewed and corrected in the chat — A read tool for one receipt with its lines and status and for the receipts waiting for review with their reasons; write tools to change, add or remove a line (the total follows as on the receipt screen, F15.6), to mark a receipt reviewed and to delete a receipt, each a card saved through the receipt service; the answer card links to the receipt; tests that another user's receipt is never found (N2). Checked at 375, 768 and 1280 px.

### F21.7 — Everything by voice, approved on a card

*Requirements: —* · *Blocked by: F21.1, F23.15, F12.8*

Anything the user can create or change on a screen can be asked for in the chat — incomes, bills, the budget, goals, accounts and their rules — and removed too, the user's account and settings excepted. Nothing is written until a card shows what was understood: it looks like the screen it belongs to, every field on it can be changed, and Approve (a tap, or saying "approve") saves it. Intent decides the branch the agent takes (an agent graph; LangGraph open source is the candidate).

**Demonstrated by:** Say "raise the budget to 2 500 and stop the gym bill": two cards, change one amount, say "approve"; Plan shows both.

- **F21.7.1** Reusable approve cards — One card component per entity built from the same pieces as its screen (Plan rows, the account card, the goal card), editable fields, Approve and Cancel, and approval by voice. Checked at 375, 768 and 1280 px.
- **F21.7.2** Intent routing and write tools for every entity — An agent graph (LangGraph) that first decides what the user wants — to know, to add, to change or to remove — and takes that branch with only its tools. Read, create, change and remove tools for incomes, regular incomes, bills, the budget, goals, accounts and their monthly transfers, each found by name the way the user says it, proposed as a card and saved only through its service after approval. Removing ends a rule from next month as the screens do. A test that settings and the account have no tool. Supersedes F21.6.1's "nothing is deleted" for these entities.
- **F21.7.3** The assistant as a module of its own — The assistant moves into app/assistant: a core (graph, intents, state, prompts) that imports neither the database nor FastAPI, tools per entity behind a narrow port, the conversation service and its router. A test holds the boundary; an ADR records why it is a module and why LangGraph.

### F21.8 — A receipt told, not photographed

*Requirements: —* · *Blocked by: F21.2, F21.7*

"I was at Biedronka today: milk 4, bread 5, apples 7.50" becomes a receipt card with its lines and categories; Approve stores it as a receipt of that shop with our own id, no photo, marked as told. Photos and PDFs can also be attached in the chat (F21.8.2): receipts are read as from the ＋ screen and come back in the conversation.

**Demonstrated by:** Dictate a shopping trip, fix one price on the card, approve: it is in Spending and its products in Products like any receipt.

- **F21.8.1** Told receipts — A receipt channel "told" with lines from speech or text, categorised as read ones are, proposed as a card with its lines and saved on approval. Checked at 375, 768 and 1280 px.
- **F21.8.2** Files attached in the chat — A paperclip beside the text field takes photos and PDFs (the same types and limits as the ＋ screen, several at once); they are sent through the upload pipeline as receipts, counted in the receipt quota, and the conversation shows a card for the reading that turns into a link to each receipt read, or says why one could not be read. The assistant is told what was attached so it can answer about it. Cross-user test (N2). Checked at 375, 768 and 1280 px.

### F21.9 — One AI credit wallet a month

*Requirements: —* · *Blocked by: F18.2, F21.1*

Everything the user asks of a model spends one monthly wallet of credits — reading a receipt (with its categories), a message to the assistant, a recording, a goal mapped, advice asked for, an income read from a document — each charged what it really cost, one credit for every 0.001 USD (decided 2026-10-22, ADR-0030). The free plan has 150 credits a month, the paid plan 2 500. The user never sees credits: the meter says what is left as receipts and as messages, about each. What runs unasked — proactive advice, matching products in the background — is recorded and charged to no one. One request of a free user is bounded, so the month cannot go in one go; a recording is a minute at most, timed on the screen.

**Demonstrated by:** On the free plan, ask three questions and read one receipt: "about 12 receipts or about 40 messages left" goes down by both; record for a minute and watch the timer stop it.

- **F21.9.1** Every model call recorded with what it cost — One place in the agent records each call — who, what for (receipt, categories, assistant, speech, goal mapping, advice, income document, background), the model, tokens in and out, seconds of sound — and its cost in credits from the model's own prices (LiteLLM's price table; Speech-to-Text by the minute), so no caller can forget it. An add-only migration for the table; admins and calls nobody asked for are recorded, charged to no one. Cross-user test (N2).
- **F21.9.2** The wallet, checked before every call — Credits a month per plan in settings (150 free, 2 500 paid; admins none), spent this month from the records; every action checked before its model call against what it usually costs and refused with an RFC 7807 problem saying what is left and when it renews; the receipt quota (F10.6) and assistant_messages_per_read retired into it, the service-wide daily ceiling counted in credits. A free user's one request is bounded: a few receipts an upload, fewer rounds of the assistant. ADR-0030 rewritten; domain-model updated.
- **F21.9.3** What is left, in receipts and messages — The meter on the Add screen, in the assistant and in Settings says what is left as about so many receipts or so many messages — worked out from what each really cost lately — and when it renews; when the month is spent the assistant, the microphone and reading say so calmly, and typing by hand still works. Three languages. Checked at 375, 768 and 1280 px.
- **F21.9.4** A recording a minute at most, timed — The service takes only WAV and refuses past a minute by the length its header gives, whatever the file's size; the microphone shows the time going, 0:42 / 1:00, and stops itself at the minute. Checked at 375, 768 and 1280 px.

### F21.10 — The assistant knows what the user has

*Requirements: N2* · *Blocked by: F21.7*

The assistant sees everything about the user the screens show, whatever the message wants: today read tools are offered only for questions, so "my card shows 4 100 but the bank says 3 700" finds no balance to compare (found 2026-10-21). One overview tool answers "what do you know about me?" — budget and the month so far, cards and balances, incomes and bills, goals and their progress, the family, trips, what waits for review, what is left of both AI limits — and the balance of a card can be set right by chat: the assistant asks whether the difference is only corrected, or recorded as purchases never entered, counted in the month's budget. One-off money in, money out and a move between cards by chat too.

**Demonstrated by:** Say "my Revolut card is 3 700, not 4 100": the assistant asks which of the two; choose "purchases I did not enter": a card for 400 of spending today on that card; approve; the balance is 3 700 and the month's spending 400 higher.

- **F21.10.1** Reads for every intent, and the overview — Read tools offered for every intent, not only ask, so a change can look before it proposes; an overview read tool over the services the screens use, its answer card linking to Home; tests that it reads only the caller's data (N2) and that a change message can call a read tool.
- **F21.10.2** A card's balance by chat — Write tools proposing a balance correction with a choice — set the balance only (the accounts service's adjust), or record the difference as spending today in a category the user can change, counted in the budget — a one-off top-up (money in as income on that card), a one-off withdrawal (the same choice as a correction) and a move between two cards; each a card saved through the accounts service (ADR-0024); a test that a card of another user is never found (N2). Checked at 375, 768 and 1280 px.

### F21.11 — Settings by chat

*Requirements: N2* · *Blocked by: F21.10*

Every setting the user can change on the Settings screen, by chat and through an approved card, except what guards signing in — password, email, the second factor — and deleting the account, which stay on their screens and which the assistant points to (ADR-0029). The card shows the setting as it is and as it will be.

**Demonstrated by:** Say "switch to Polish and the dark palette, payday is the 10th": three cards; approve them; the app is in Polish, dark, and Plan counts from the 10th.

- **F21.11.1** Money settings — Change cards for the currency, the usual income, the payday, the starting balance and paying one's own taxes with its rate and fixed monthly sum (F23.16), each saved through the same service as Settings; read tool for the current settings. Checked at 375, 768 and 1280 px.
- **F21.11.2** Look, language and the rest — Change cards for the language (the app switches as soon as the card is saved), the palette, dark at night and "I travel for work" (F23.12). Checked at 375, 768 and 1280 px.
- **F21.11.3** The family by chat — Cards to invite a member by address, change a member's role, remove a member and leave the family, each only where the screen allows it (F12); a read tool for who is in the family. Checked at 375, 768 and 1280 px.
- **F21.11.4** What stays on the screens — ADR-0029 accepted, replacing ADR-0025's "settings and the account have no tool": password, email, the second factor and deleting the account have none, and the assistant answers a request for them with a link to the screen; a test that no tool touches them; the prompt's rule on settings rewritten.

### F21.12 — Admin by chat

*Requirements: N2* · *Blocked by: F21.10, F18.6*

An admin does in the chat what the admin console does (F18.6) — find a user by address, see their account facts and usage, confirm the address, send the confirmation or a reset link, grant a paid plan for a time or take it back; a super admin also appoints and removes admins. The tools are offered only to an admin session signed in with the second factor, every action is an approved card recorded in the admin log, and no tool ever reads another user's receipts or money (N2).

**Demonstrated by:** As an admin, say "give anna@example.com the paid plan until December": a card; approve; the grant is on her account and in the admin log.

- **F21.12.1** Admin tools behind the admin role — Read and write tools over the admin service, registered only for admins with a second factor (super-admin tools only for super admins); cards for each action, recorded in the admin log as from the console; tests that a user who is not an admin is never offered them and that no admin tool returns receipts, incomes or balances (N2). Checked at 375, 768 and 1280 px.
- **F21.12.2** The admin console's overview by chat — "What is going on in the admin console?" is answered: read tools for the dashboard's figures over a period (visits, sources, platforms, sign-ups, receipts read, active and returning users — counts only), the reported assistant replies, and, for super admins, the admin log. An admin signed in without the second factor is told to sign in again with the code instead of a vague answer. The evaluation set gains admin dialogs, run with the session's access.

### F21.13 — An assistant that finds what the user means

*Requirements: N2* · *Blocked by: F21.10*

Measured on 2026-10-22 against the real model and tools: "update the balance on my card for expenses", "on the first card", "the one I pay for shopping with" all ended in "name the card", turn after turn. The model was given cards without the role that tells which one pays for purchases, was told to pass the user's own words to the tools, and the tools matched names only; it read through a JSON protocol of our own instead of the provider's function calling, behind a classifier that could withhold tools. Now the assistant knows what the user has before it answers — every card with its role, kind, balance and place in the list, the bills, incomes, goals, trips and categories — calls the provider's own tools in a loop until it has what it needs, names things by their real names, and when more than one thing fits asks with a card of options to tap rather than a question to type. How well it does is measured, not felt: a set of dialogs scored before and after.

**Demonstrated by:** Say "update the balance on my card for expenses, the bank says 3 500": the card for the purchase card appears at once; say "update the balance on a card": a card with the three cards to tap.

- **F21.13.1** The provider's own tool calling, in a loop — The graph calls the model with every tool as a function (LiteLLM tools, which Gemini and OpenAI-compatible local models both take), runs the reads, checks each write and records it as a proposed card, answers the model with each result, and loops until it answers in words, at most eight rounds; the intent classifier and the second look go. A refused write is answered with why and what there is, never dropped. ADR-0032 supersedes ADR-0025's structured-output calling and ADR-0028's classify node; domain-model and overview updated.
- **F21.13.2** What the user has, in every turn — A compact summary of the user's things in the system prompt — cards with kind, balance, which pays for purchases and their order as the Accounts screen lists them; regular incomes, bills, goals, trips and categories by name — so the model resolves "the card for expenses", "the first one", "my savings" itself and passes real names; finding by name also understands the purchase card and a card's place in the list, as a safety net. Tests that only the caller's things appear (N2).
- **F21.13.3** A question with options to tap — An `ask` tool: when more than one thing fits or something is missing, the assistant asks with a card of options; tapping one sends it as the user's answer and the conversation goes on. A refused write lists the candidates for it. Checked at 375, 768 and 1280 px.
- **F21.13.4** The assistant measured — scripts/evaluate_assistant.py: a seeded user and about thirty dialogs in Ukrainian, Polish, English and Russian — balances, cards by role and by place, bills, budget, goals, questions — each with the tool and arguments expected or a question with options; run against the configured model, scored per dialog and overall with time and tokens, the baseline and the result written in the ADR.
- **F21.13.5** The assistant behind the middle button — The phone's middle button and the side menu's main button open the assistant, with an icon that says it is one; adding a receipt by hand stays one tap away — a button in the assistant's header, the paperclip, and a plain item in the side menu — and the Add screen keeps everything it has. Checked at 375, 768 and 1280 px.

### F21.14 — Answers drawn like the screens

*Requirements: N2* · *Blocked by: F21.10, F8.11*

An answer about money shows the thing itself, drawn the way its screen draws it, beside the words: the cards and their balances as the Accounts screen shows them, the purchase card marked; the month as Home's ring — spent, bills, what is left of the budget; each goal with its progress bar; products as a table to pick from. Charts for spending by category already come with their answers (F21.4). Each drawing links to its screen, and is built from what the read tool found, never from the model's words.

**Demonstrated by:** Ask "what's on my cards?": the two cards with their balances; "how is my month?": the ring; "how are my goals?": the goals with their bars; "which snacks did I buy?": a table of them.

- **F21.14.1** Cards, month, goals and products as answer cards — The accounts, overview/month, goals and products read tools leave an answer card with what they found — screen "accounts", "month", "goals", "products" — drawn by the client from shared pieces of the screens (the account card, the month ring, the goal meter, a product row), each linking to its screen; three languages; tests that a card carries only the caller's data (N2). Checked at 375, 768 and 1280 px.

### F21.15 — Receipts and categories by chat

*Requirements: C4, C6, N2* · *Blocked by: F21.13, F5.6*

"Show my last receipt", then "what category is it?", then "make a Subscriptions category and put it there" broke at the second step: the receipts tool gave no categories and nothing could change one. The assistant reads a receipt with its lines and their categories, refers back to "that receipt" from earlier in the conversation, and proposes a new category and moving a receipt or a line into one — each on a card the user approves, as every change is (ADR-0025).

**Demonstrated by:** Ask "my last receipt": YouTube, 60. "Which category?": Other. "Create Subscriptions and move it there": two cards, the category and the move; approve both: Spending shows 60 under Subscriptions.

- **F21.15.1** A receipt with its lines and categories — The receipts tool gives each receipt a reference the next turn can use, and a receipt tool gives one receipt's lines with their categories; a categories tool lists the user's categories. Only the caller's own and their family's shared receipts (N2).
- **F21.15.2** A new category and moving into one, on cards — Cards to add a category (the Categories screen's rules) and to move a whole receipt, or one of its lines, into a category — new or existing — as a correction the categoriser learns from (C4). A move into a category proposed in the same turn waits for that card. Three languages; checked at 375, 768 and 1280 px.
- **F21.15.3** The conversation that broke, kept as a test — The three-step conversation above, and a few like it, added to the assistant's evaluation dialogs; they pass on the production model before this ships.

### F21.16 — One door for whatever is sent

*Requirements: N2* · *Blocked by: F21.15, F23.21*

The ＋ and the assistant are the same reader: whatever a user drops in — several photos at once, one photo of several receipts laid on a table, a long receipt in parts, a bank app's screenshot of a transfer they made or money they got, a payslip — it works out what each thing is and proposes the right cards: receipts, an expense paid by transfer, an income. When it cannot tell (a transfer out, or a top-up of the user's own card?) it asks, offering the answers to tap, and asks which card when it matters. Found by the first outside tester: three receipts photographed together were read as one, a VND transfer was refused as "not a receipt", and a re-upload of the stuck three-receipt photo was refused as a duplicate of a receipt nowhere on screen.

**Demonstrated by:** Photograph three receipts on a table and drop in a bank screenshot of a transfer: the ＋ proposes three receipts and one expense "transfer, 300 000 VND", each checked and saved; the same files attached to the assistant give the same cards.

- **F21.16.1** What each file is — Every photo or PDF page sent through the ＋ or attached in the chat is first told apart: one or more receipts, money sent (a transfer or a payment), money received, a payslip, or something else. Money sent becomes an expense of one amount with no lines, marked as a transfer, with its date, currency and the payee as merchant; money received goes the income way (F23.21.2: a card is asked for when there is none). Not sure which — asked with options to tap, never guessed; something else is refused saying what it looked like. The same port and rules for the upload and the assistant (OCP: a new kind plugs in). Three languages; checked at 375, 768 and 1280 px.
- **F21.16.2** Many receipts in one go — One photo holding several receipts becomes several receipts; several photos sent at once are grouped by the reader into receipts, the parts of one long receipt staying one (B2-B4, B9 unchanged). The review shows each receipt found with the photo it came from, to correct or drop before saving. The assistant takes several attachments in one message, up to the upload's limit. The quota counts each receipt read.
- **F21.16.3** An upload never strands — Uploading always ends on the review or with a reason and what to do. A refusal as a duplicate names and links the receipt already stored; a file whose reading never finished, or was dropped, is not a duplicate and can be sent again. Tests for both.
- **F21.16.4** Measured, and written down — The reading evaluation gains a photo of three receipts, a long receipt in two photos, a transfer sent and one received from bank apps (VND, PLN, UAH) and a payslip, scored on what each was taken for; the assistant's evaluation gains the same as attachments. An ADR for telling files apart and asking when unsure; the domain model (a transfer expense) and the overview's ingestion flow updated.

### F21.17 — The family by chat

*Requirements: N2* · *Blocked by: F21.13, F12.5*

The family is the product's own idea, but the assistant could not answer "what did my wife buy today?". It answers about any member of the user's family — what they bought, where, how much, in a period — finding who is meant by a name however it is said (a first name, a short form, another language, "my wife" once the user has said who that is), asking with the members' names to tap when more than one fits or none does. Only what the family already shares: a member's private receipts stay a sum (ADR-0017).

**Demonstrated by:** In a family with Олена and Максим ask "що сьогодні купувала Лена?": her shared receipts of today with their lines. Ask "and my son?": a question with Максим to tap.

- **F21.17.1** A member's purchases — A read tool gives one member's shared receipts and lines over a period, and the totals of their private ones without detail; the member is named, not given by id, and resolved by name, short form or transliteration, else asked about with the members' names. Tests that a private receipt's lines never come back and that someone outside the family is never found (N2).
- **F21.17.2** Who "my wife" is — When the user says how they call a member ("Олена — моя дружина"), it is kept on the user's own side of the family, never shown to that member, and used to resolve "my wife" later; changed or forgotten by saying so. Add-only migration.
- **F21.17.3** Family dialogs in the evaluation — The assistant's evaluation gains a seeded family and dialogs in three languages: a member by a short name, by a relation already told, an unclear one asked about, and a private receipt not revealed.

---

## E22 — Android App

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

The service in Google Play, where advertising needs no domain (E19) and a phone's camera, haptics and share sheet are at hand. The app is the existing web client wrapped in Capacitor — one codebase, the same API in the cloud — with one platform module the rest of the client asks what the device can do, so a feature checks "is there a camera, can it vibrate, was a file shared in" in one place and the web build keeps working unchanged. Published under the business's developer account, registered as an organisation with a D-U-N-S number (which spares the closed test with twelve testers a personal account needs), with a support mailbox of its own as the public contact. Built, signed and released by GitHub Actions after the first upload by hand. Next after F17.7, before E19's in-app ads and E21.

### F22.1 — Developer account and store listing

*Requirements: —* · *Blocked by: F17.7, F17.9, F17.10*

A Google Play developer account for the JDG as an organisation (D-U-N-S number asked for early: it takes days), a dedicated support mailbox as the public contact, and the listing: name, descriptions and screenshots in three languages, icon, content rating, the privacy policy's address, the Data safety form answered from ADR-0020, and the account deletion address Google asks for (F17.9.1).

**Demonstrated by:** Open the listing in Play: descriptions in Polish, Ukrainian and English, the support address, the privacy policy link opening /privacy, and the Data safety section.

- **F22.1.1** Account, listing and Data safety — The steps and answers recorded in docs/ (what each Data safety question was answered and why, from ADR-0020), the listing texts in three languages kept in the repository, screenshots at phone and tablet sizes; an ADR for the organisation account, D-U-N-S and what the listing publishes about the business.
- **F22.1.2** The support mailbox in the service — A support_email setting the contact form (F17.10.2) mails instead of admin_emails, named on the Help page and in the privacy policy; Terraform and the deployment documentation updated.

### F22.2 — The app on the phone

*Requirements: —* · *Blocked by: F22.1*

The client built into an Android app with Capacitor: the API's address and the app's origin in CORS, Android's back button moving back through the screens, the status bar and splash in the service's colours, the offline page, and links from letters (confirming an address, resetting a password) opening the app through Android App Links (assetlinks.json on Firebase Hosting). Everything that differs on a device goes through one platform module, so screens never ask "am I in the app".

**Demonstrated by:** Install the app, sign in, follow the confirmation link from the letter on the same phone and land in the app with the address confirmed; press back through three screens.

- **F22.2.1** Capacitor project and the platform module — The Android project from the existing build, the platform module (web and native implementations behind one interface, tested with both), CORS for the app's origin, the back button, status bar, splash and App Links; the architecture overview updated. Checked on a phone and a tablet.
- **F22.2.2** Camera, haptics and sharing a receipt in — The native camera for receipts, a short vibration when a receipt is read or saved, and "Share → Budget Agent" for images and PDFs from other apps opening the upload flow with them — each behind the platform module, the web build unchanged.

### F22.3 — Building and releasing the app

*Requirements: —* · *Blocked by: F22.2*

After the first upload by hand, every merge to main builds a signed app bundle and puts it on Play's internal track; promoting a build to production is one manual run of the same workflow. No key file anywhere: GitHub signs in to Google through Workload Identity Federation, as the Cloud Run deploy does, as a service account added to the Play Console; the upload key lives in GitHub's secrets, Google holding the app signing key (Play App Signing).

**Demonstrated by:** Merge a change to main and find the new version on the internal track a few minutes later; promote it to production from the Actions tab.

- **F22.3.1** Release identity in Terraform — The publishing service account and its Workload Identity binding for the repository, in infra/terraform; the steps to add it to the Play Console and to store the upload key in GitHub documented.
- **F22.3.2** Build and release workflow — A GitHub Actions workflow building the web client and the signed AAB (versionCode from the run number), uploading it to the internal track on merge to main and to production on a manual run; the release documentation updated.

### F22.4 — Passing Google Play's review

*Requirements: —* · *Blocked by: F22.2*

A rejection costs days, so every Play policy the app touches is met and written down before the first upload: the target API level Play requires for new apps, permissions kept to the camera (gallery photos through the system photo picker, no storage or media permission), the Data safety form, account deletion both in the app and at a web address, the Financial features declaration, the content rating, and the generative AI rules — the assistant's replies can be reported from the app. The app does more than the website (camera, sharing in, haptics, offline), so it is not a wrapped page under the minimum-functionality policy.

**Demonstrated by:** Open docs/mobile/play-review.md: each policy, what the app does about it and where; the pre-launch report of the internal build shows no policy or accessibility warnings.

- **F22.4.1** Play policy checklist — docs/mobile/play-review.md: target API level, permissions declared and why, Data safety answers (from ADR-0020), account deletion (in app: Settings; on the web: its address), Financial features declaration, content rating answers, ads and families policy (not for children), the store listing's metadata rules — each checked against the current policy page with its date, and the app's answer.
- **F22.4.2** Reporting an assistant reply — Every assistant reply can be reported from the chat (offensive, wrong, other); the report keeps the reply and the reason for the admins, never the conversation around it, and the admin console lists reports. Required for generative AI apps by Play and asked for by App Review. Three languages; checked at 375, 768 and 1280 px.
- **F22.4.3** Permissions and the photo picker — Gallery images come through Android's photo picker, so the manifest asks for the camera alone; a denied camera falls back to the picker with a line saying so. The pre-launch report of the internal track run and its findings fixed.

### F22.5 — An app that feels like Android

*Requirements: —* · *Blocked by: F22.2*

The same screens, behaving the way Android apps do rather than like a page: edge to edge under the status and navigation bars (Android 15 enforces it), the predictive back gesture, the keyboard pushing the form up instead of covering it, no text selection or long-press callouts on buttons, no rubber-band overscroll or page zoom, the system font size respected, haptics on the moments that matter, and the native date and share sheets. Everything through the platform module, the web build unchanged.

**Demonstrated by:** On a phone: swipe back from a receipt with the predictive preview, type in the expense form with the keyboard open and the Save button visible, raise the system font size and find nothing cut off.

- **F22.5.1** Edge to edge, back gesture and the keyboard — Safe-area insets from the device applied by the shell, the predictive back gesture wired to the router, the keyboard resizing the content, status bar colours following the palette. Checked on a phone and a tablet, light and dark.
- **F22.5.2** Native touches — No selection or callouts on controls, no overscroll or zoom, the native date picker, haptics on save and on a receipt read, the system share sheet for exports; a test of the platform module for each, web and native.

---

## E23 — Improvements

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

What using the product feels like, after competitors were compared on the App Store (Fleur, Bloomly, Spendee, Buddy, Copilot; Billy, the Polish line-item app, at 3.7 stars): the features were stronger than theirs, the screens weaker. One branch, improvements, built in one go from the mockups at https://claude.ai/artifact/J4TvghztEyxSjmfyNWXqet — a new navigation, palettes the user chooses, colourful interactive charts, a first sign-in that sets things up, money coming in as well as going out, and a manual discount on a receipt. No issue per change: this epic lists what was improved.

### F23.1 — Palettes and chart colours

*Requirements: —*

Six palettes — Midnight (the default, today's dark), Daylight (today's light), Rose, Lavender, Sage and Ocean — each with its own series for charts, kept on the account so every device shows the one chosen, with "dark at night" following the phone.

**Demonstrated by:** In Settings tap Rose: every screen and chart turns rose at once, and stays so after signing in on another browser.

### F23.2 — Navigation by what people do

*Requirements: —* · *Blocked by: F23.1*

Home · Spending · ＋ · Products · Plan in a bottom bar on a phone and a side menu on a tablet and desktop; Receipts becomes the history behind "All receipts", categories to review become a card on Home, trips move into Plan and Settings. Home is «Головна» in Ukrainian and «Start» in Polish.

**Demonstrated by:** On a phone reach every former screen from the five tabs; on a desktop the same from the side menu.

### F23.3 — Home

*Requirements: —* · *Blocked by: F23.2*

A ring with what is left to spend this month, income and budget editable in place, the categories as coloured tiles, the price change worth knowing, and the latest purchases.

**Demonstrated by:** Open the app: what is left this month is the first thing read; tap Income, change it, and the ring follows.

### F23.4 — Spending

*Requirements: —* · *Blocked by: F23.2*

An interactive ring by category with last month beside each, spending by day, and the way into every receipt.

**Demonstrated by:** Tap Eating out: the ring highlights it and its total shows in the middle.

### F23.5 — Products

*Requirements: —* · *Blocked by: F23.2*

Price changes across everything bought, what is bought most, which shop the usual basket is cheapest in, and exploring several products together — today's exploration, kept whole, in the new look.

**Demonstrated by:** Open Products, see the milk that got dearer, open Explore, pick milk and coffee and read what they cost by month.

### F23.6 — Adding a receipt

*Requirements: —* · *Blocked by: F23.2*

＋ offers the camera where there is one, photos and PDFs, the forwarding address, and dropping a file on a desktop; reading shows its progress, and the review is the receipt's lines in their categories.

**Demonstrated by:** On a phone, ＋ → Take a photo opens the camera; on a desktop drop a PDF on the page.

### F23.7 — A discount the receipt does not show

*Requirements: —* · *Blocked by: F23.6*

Paid 69 of the 169 printed — a gift card, a voucher, a deal at the till: the user enters the discount on the receipt, it is spread over its lines in proportion (or only over the lines chosen), the month, categories and statistics count what was paid, and price history keeps the shelf price.

**Demonstrated by:** Add a 100 zł discount to a 169 zł receipt: the month grows by 69 zł, and milk's price history is unchanged.

### F23.8 — Settings

*Requirements: —* · *Blocked by: F23.1*

Preferences become Settings: the palette, money (currency, income, payday), language, household, work trips, account and security, and the user's data, in sections that read at a glance.

**Demonstrated by:** Open Settings from the avatar and change the palette, the language and the income.

### F23.9 — First sign-in

*Requirements: —* · *Blocked by: F23.1, F23.10*

Once, after the first sign-in, and skippable: language and currency guessed from the browser, the palette, the usual monthly income and payday, and two-factor sign-in. Skipping keeps the defaults.

**Demonstrated by:** Register in a Polish browser: Polski and PLN are chosen, pick Lavender, and the app opens in it; sign in elsewhere and the onboarding does not come back.

### F23.10 — Money coming in

*Requirements: —*

Income as entries — when, how much, from what — summed per month, the usual monthly income standing in until the month's arrive; changed in place on Home and in Plan. Months stay calendar months; payday is kept for later.

**Demonstrated by:** Add the salary on Home, see what is left grow; next month it shows the usual income until this month's arrives.

### F23.11 — Income from a document

*Requirements: —* · *Blocked by: F23.10*

A payslip or transfer confirmation sent through ＋ or by email is recognised as income, not a receipt, and shown as a card to confirm before anything is written; only the amount, the date and the source are kept, the file deleted once read.

**Demonstrated by:** Forward a payslip PDF: the card says "Income: 6 200 zł from ACME, 10 October"; save it and Home counts it.

### F23.12 — Holidays and business trips apart

*Requirements: —* · *Blocked by: F23.2*

Personal trips are Holidays in Plan, with their budget and day-by-day spending; business trips, with per diem and the settlement, appear once "I travel for work" is on in Settings.

**Demonstrated by:** Plan shows the holiday; turn on work trips in Settings and the business trip list appears.

### F23.13 — Goals that are easy to set

*Requirements: —* · *Blocked by: F23.2*

A new goal starts from four large choices instead of selects, asks name, amount and date with buttons, and is checked before it is saved — doable, or a stretch with where the money could come from.

**Demonstrated by:** Ask for 8 000 by June: "A stretch", with two changes that close the gap.

### F23.14 — Balance

*Requirements: —* · *Blocked by: F23.10*

What the user has now: a starting balance entered once — in the first sign-in or in Settings, explained as "money on your accounts today", not income — that then moves by itself, up with every income entered or read, down with every purchase counted, shown on Home.

**Demonstrated by:** Start with 5 000 zł; store a 169 zł receipt and the balance reads 4 831 zł; add the salary and it grows by it.

### F23.15 — Accounts and money between them

*Requirements: —* · *Blocked by: F23.14, F12.8*

Where the money is, for a family with a business too: accounts the user names (personal, business, deposit — a deposit just an amount for now), each personal or shared with the family. Money arrives ON an account FROM outside (income) or from another own account (a transfer, neither income nor spending). A business account carries the tax rule (a rate per payment in — common ones offered, any one allowed), so a payment shows the tax and the clean amount at once; regular bills (ZUS, an accountant) and regular transfers ("6 000 to our card on the 10th") belong to an account and post themselves on their day — a day already past this month starts next month. A regular income is exact or about (230 000 a year ÷ 12): an "about" one shows as expected on its day until the real amount is confirmed; a bonus is a one-off. Every account keeps a bank-like history; this month's entries can be changed, earlier months are closed. Income from email whose account is unknown waits in "To check" with the account to pick. Without accounts, everything works as today.

**Demonstrated by:** Add a shared business account with 5 % tax, ZUS 1 600 on the 20th and 6 000 to "Our card" on the 10th; press ＋, enter 10 000 from a client and see −500 tax, 9 500 clean; on the 10th the transfer appears in both histories by itself.

- **F23.15.1** Accounts, entries and dated rules — Accounts (name, kind, owner or household, opening amount), entries (income from outside, transfer between own accounts, bill, adjustment) and monthly rules (income exact/about, bill, transfer) posted by date — never for a day already past when the rule is made; this month's entries editable, earlier months closed; the tax rule on business accounts. The balance (F23.14) becomes the sum of the accounts the user sees when there are any. Domain model and an ADR; ownership and cross-household tests (N2).
- **F23.15.2** Accounts screens — Where the money is (canvas F_Accounts), one account with ＋ Money in, Move and its history (F_Account), its rules (F_Rules), and "To check" for expected income and email income without an account (F_Check). Checked at 375, 768 and 1280 px.

### F23.16 — Paying one's own taxes

*Requirements: —* · *Blocked by: F23.10, F23.14*

For a sole trader or contractor, whose income comes before tax: a switch in Settings with their own rate and an optional fixed sum a month; each income says whether the tax comes out of it, "left to spend" counts what is theirs to keep, and taxes paid leave the balance without counting as spending.

**Demonstrated by:** Set 12 % and 1 600 zł a month, see 20 000 zł earned leave 16 000 zł to live on, and the balance say how much of it is still owed in taxes.

### F23.17 — Regular incomes

*Requirements: —* · *Blocked by: F23.10, F23.14*

A salary, a side job, a pension — set once in Settings or the first-sign-in setup, counted in every month by themselves, the balance gaining each on its day; anything that comes on top is added by hand through ＋ or from a document.

**Demonstrated by:** Add a 10 000 zł salary on the 10th and a 1 000 zł side job; next month both count without entering anything, and 500 zł added on top joins them.

### F23.18 — Regular bills

*Requirements: —* · *Blocked by: F23.17*

Rent, subscriptions, a loan — set once, gone every month by themselves: off what is left on Home and in Plan and off the balance on their day, never counted as purchases in Spending's figures, and listed there in their own section.

**Demonstrated by:** Add rent of 3 000 zł on the 5th; Plan shows spent · bills · free, and the balance drops by 3 000 on the 5th of each month.

### F23.19 — Where receipts and categories live

*Requirements: —*

Not decided yet. Spending mixes the receipts list and the categories behind one switch, which reads as clutter. Keep the receipts list (a receipt is still fixed or deleted from it) and the review of uncertain items; move managing categories and the remembered rules to Settings. Three ways are drawn in the design canvas (https://claude.ai/artifact/J4TvghztEyxSjmfyNWXqet): A — receipts stay in Spending, items sorted card by card; B — a clean Spending with a category drill-down and receipts as their own history with search and filters; C — one "To check" inbox for receipts that do not add up, items without a category and income from email. Pick one with the user, update docs/design, then build it.

**Demonstrated by:** Open Spending and see no receipts/categories switch; fix or delete a receipt from its history; sort uncategorised items one at a time; rename a category in Settings.

### F23.20 — A receipt paid from another card

*Requirements: —* · *Blocked by: F23.15*

Purchases come off the purchase card (F23.15): one's own, else the family's shared one. Sometimes a receipt was paid from another — fuel or a cola on the business card. Changing a receipt's card moves its amount to that account's history and balance; the ledger already reads purchases per buyer, so only where one receipt lands changes.

**Demonstrated by:** Open a fuel receipt, choose the business card, and see it leave "Our card" and appear in the business account's history that day.

### F23.21 — Cards when wanted, income on a card, bills weekly too

*Requirements: —* · *Blocked by: F23.15, F23.17, F23.18*

Forcing a card was the biggest step between signing up and using the product: a person who only wants to see whether a month fitted the budget had to keep books. Use now comes in levels set by what the user has made, with no switch: a budget alone — what was spent, bills included, against the monthly budget; a card — balances and what came off them; a business card — taxes and transfers. Income is bookkeeping, so it always lands on a card, and adding it with none offers to make one in the same step. Regular bills are spending with or without a card, shown as their own part of the budget ring. Bills and regular incomes come weekly as well as monthly. Supersedes ADR-0024's "every sum is on an account".

**Demonstrated by:** Sign up, skip the card, set a budget of 2 000 and a monthly internet bill of 60: Home shows the ring with purchases and bills, no balance. Add a salary: the app asks where it lands and makes "My card" in the same dialog; the bill is offered to the card too. Add a weekly gym bill of 50 on Mondays: October counts it four times, 200.

### F23.22 — A day's receipts from the chart, and the chart drawn three ways

*Requirements: —* · *Blocked by: F23.4*

Tapping a day on Spending's day-by-day chart only named its sum, so the obvious next question — what was bought that day — needed a trip to Receipts and a date filter. The tap now lists that day's receipts under the chart. People also read a month differently: some want columns, some a list of days, some a calendar, so the chart can be drawn each way and remembers the choice.

**Demonstrated by:** On Spending, tap 14 October: its three receipts appear under the chart, each opening its details. Switch the chart to Days: the same month as rows, a bar per day; to Calendar: the month as weeks, darker for bigger days. Reload: it stays on Calendar.

- **F23.22.1** The receipts of the day tapped — Tapping a day with spending lists that day's receipts under the chart (shop, total, opening the receipt's details), read from the receipts list for that one day; a day with none says so. The day opened at first shows none until tapped. Checked at 375, 768 and 1280 px.
- **F23.22.2** Columns, days or a calendar — A switch above the chart: Columns (today's bars), Days (a row a day, the bar across, the sum at its end) and Calendar (the period's weeks, Monday first, each day shaded by its share of the biggest). Every view taps to the same day and its receipts. The choice is kept in this browser only, as a convenience the privacy check knows of. Checked at 375, 768 and 1280 px.
- **F23.22.3** The family's chart the same way — The family's day-by-day chart (F12.5) gets the same three views and tap: the tapped day lists the family's receipts of that day, each saying whose it is (the viewer's, or the member's first name), from the shared receipts only — a member's private spending stays a sum without a day (ADR-0017). A test that a private receipt never appears there (N2). Checked at 375, 768 and 1280 px.

### F23.23 — Money set up the way a stranger reads it

*Requirements: —* · *Blocked by: F23.21*

The first outside tester could not tell what onboarding's income step asked: they typed the amount into "what is it", read "each time, USD" as nothing, and never noticed a card was being made — then Home called that card below zero. The rule stays F23.21's: no card unless the user makes one; income asks where it lands and offers to make one. What changes is that every step says so plainly: a card is just a name the user will recognise, never a card number, and each name is the user's own once. Receipts that do not count yet are seen, with why.

**Demonstrated by:** Sign up as a new user in Ukrainian: the income step reads "Назва доходу (зарплата, фріланс)" and "Сума за раз"; adding it says "створимо картку — лише назва, без номера"; skipping leaves no card, and the summary lists exactly what was saved.

---

## E25 — iOS App

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

The service in Apple's App Store from the same Capacitor build as Android (E22), through the same platform module, so a screen never asks which phone it is on. Taken first if Google's organisation account stays blocked on the D-U-N-S address. App Review rejects wrapped websites, purchases outside Apple's payments and data sent to an AI without the user's consent, so each guideline the app touches is met before the first submission. A native rewrite of either app is E26, planned only once the stores accept these.

### F25.1 — Apple developer account and the App Store listing

*Requirements: —* · *Blocked by: F17.7, F17.9*

An Apple Developer Program membership — as an organisation it needs a D-U-N-S number too, so the decision between that and an individual membership under the author's name is recorded — and the App Store Connect listing: name, subtitle, descriptions and screenshots in three languages, the privacy policy and support addresses, the age rating, the App Privacy answers, and a reviewer account with a month of receipts.

**Demonstrated by:** The listing in App Store Connect in three languages, its App Privacy section matching docs/mobile/app-store-review.md, and the reviewer account signing in to real data.

- **F25.1.1** Membership, listing and App Privacy — An ADR for organisation or individual membership; the listing texts in the repository; App Privacy answers from ADR-0020; screenshots for the phone and iPad sizes App Store Connect asks for; the reviewer account seeded like the demo one and its sign-in given in the review notes.

### F25.2 — The app on the iPhone

*Requirements: —* · *Blocked by: F22.2*

The iOS project from the same build and platform module as Android: safe areas around the notch and the home indicator, the swipe-back gesture between screens, the status bar and launch screen in the service's colours, the native camera, haptics, a Share Extension so "Share → Budget Agent" from Photos or Files opens the upload, Universal Links (apple-app-site-association on Firebase Hosting) for the letters' links, and the keyboard behaving as in native forms.

**Demonstrated by:** On an iPhone: share a photo from Photos into the app and see it read; open the confirmation link from Mail and land in the app; swipe back through three screens.

- **F25.2.1** The iOS project in the platform module — The Xcode project from the existing build, the platform module's iOS answers, safe areas, swipe back, status bar, launch screen, keyboard and Universal Links; the architecture overview updated. Checked on an iPhone with a notch, a small iPhone and an iPad.
- **F25.2.2** Camera, haptics and the Share Extension — The native camera, haptics on save and on a receipt read, and a Share Extension for images and PDFs handing them to the upload flow — each behind the platform module, the web and Android builds unchanged.
- **F25.2.3** The iPhone app feeling native — What F25.2.2 left: the Share Extension ("Share → Budget Agent" from Photos, Files or Mail; images and PDFs only, through an App Group, opened on the add-a-receipt screen and never mixed into a receipt under review); the camera asking for access before the viewfinder opens, so the system's question comes on the first tap, with a line pointing to Settings when it is refused; haptics where native apps give them — success and failure of every action, a changed tab, segment, switch or chart day, the ＋ button; pages that stretch and spring back at both ends, short ones too, with the page's own colour past the edge. The permission texts in en, uk and pl. Checked in the simulator; haptics on a phone.

### F25.3 — Passing App Review

*Requirements: —* · *Blocked by: F25.2*

Every guideline the app touches met and written down before the first submission: minimum functionality (4.2 — the app does what the site cannot: camera, sharing in, haptics, offline); account deletion inside the app (5.1.1); no buying, prices or links to buy the paid plan anywhere in the app (3.1.1, 3.1.3) while payments are outside the stores; asking before personal data goes to a third-party AI (5.1.2), naming the provider; the privacy manifest declaring the APIs the app and its plugins use; export compliance (standard HTTPS only); no tracking, so no tracking prompt until ads come.

**Demonstrated by:** Open docs/mobile/app-store-review.md: each guideline, what the app does about it and where; the first TestFlight build passes Apple's automated checks with no warnings.

- **F25.3.1** App Review checklist and privacy manifest — docs/mobile/app-store-review.md for guidelines 2.1, 2.3, 3.1, 4.2, 5.1.1, 5.1.2 and export compliance, each checked against the current guidelines with its date; PrivacyInfo.xcprivacy with the required-reason APIs of the app and its plugins; ITSAppUsesNonExemptEncryption set to false.
- **F25.3.2** Asking before receipts go to the AI — Before the first receipt, voice message or chat goes to the model, the app says what is sent, to whom (Google's Gemini on Vertex AI) and why, and asks; the answer is kept on the account with its date and can be withdrawn in Settings, which stops every AI feature until it is given again. Applies on the web too, so the rule is one. ADR and the privacy policy updated; three languages; checked at 375, 768 and 1280 px.
- **F25.3.3** No paid plan offered inside the app — Inside the store apps, nothing names a price, a purchase or a way to buy the paid plan, and no link leads to one; what is left of the AI credits is still shown. The platform module says when the client is a store app; a test that no such text or link renders there.
- **F25.3.4** AI features off until allowed — Without the AI allowed, the camera's reading, the assistant and every AI button show as off with one line and a way to allow it, instead of failing on use; the consent dialog says that "not now" leaves them off until allowed in Settings. The client reads the profile's consent, which the server already returns — not a claim in the session token, which would stay "allowed" for its lifetime after a withdrawal; the server keeps refusing as now. Three languages; checked at 375, 768 and 1280 px.

---

## E26 — Native Apps

**BRD sections:** — · **Phase:** 3 · **Scope:** Out of scope

Once the Capacitor apps are accepted and used, each moves to its own platform's toolkit — Kotlin with Jetpack Compose on Android, Swift with SwiftUI on iOS — screen by screen, against the same API and its generated schema, keeping the platform module's contract as the list of what each must do. Planned after E22 and E25, not before: the stores' review and real use decide which screens are worth rewriting first.

### F26.1 — Android in Kotlin and Compose

*Requirements: —* · *Blocked by: F22.5*

The Android app rewritten natively, screen by screen, starting with those real use shows to matter most; the Capacitor build stays until the native one covers it.

### F26.2 — iOS in Swift and SwiftUI

*Requirements: —* · *Blocked by: F25.3*

The iOS app rewritten natively, screen by screen, the same way as Android.

---

## E24 — Bugfixes

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

Bugs found while using the product, fixed on a bugfix branch without an issue each; every batch is listed here so the board shows what was fixed and when.

### F24.1 — Fixes of 15–16 October 2026

*Requirements: —*

Product search and selection, product names carrying a date, a saved selection offering Save again, the receipts page's default period and order, and endless loading on a phone after the server's cold start (PR #519).

**Demonstrated by:** No screen of its own — each fix is seen where the bug was.

### F24.2 — Fixes of 23 October 2026

*Requirements: —*

On a phone the bottom bar drifted with the scroll after typing in a field: Safari zooms into any field under 16px and stays zoomed. Home's chat button sat alone in the middle of the header instead of beside the avatar.

**Demonstrated by:** No screen of its own — each fix is seen where the bug was.

### F24.3 — Fixes from the first outside test, 24 October 2026

*Requirements: —*

A tester new to the product, and the owner's family, found these on the website. Onboarding's income step saved the income but not the card's balance now, so Home showed the new card 122 below zero and warned to top it up, and the summary said "income: not set, accounts: not set". "Send again" for the confirmation letter sent nothing three times, and the address stayed "not confirmed" after it was confirmed until the page was reloaded. A receipt refused because the AI was not allowed showed a server text in English to a Ukrainian user — every refusal on the upload screen is worded from its code in the user's language. A receipt dated years back was stored in its own month, where the tester could not find it: it stays there, and saving it says which month it went to, with a link. The confirmation notice said "household" ("домогосподарство"), where the tabs say "family".

**Demonstrated by:** No screen of its own — each fix is seen where the bug was.

