# Delivery backlog

> Generated from [`backlog.yaml`](backlog.yaml) by `scripts/backlog_sync.py render`.
> Edit the YAML, not this file.

17 epics · 110 features · 213 tasks written so far.

14 epics are in the diploma project's scope; 3 are planned but out of it.

| Epic | Title | BRD | Features | Groomed | Phase | Scope |
|---|---|---|---|---|---|---|
| E0 | Foundation & Delivery Platform | — | 10 | yes | 1 | Diploma |
| E1 | Identity & Account | BR-7, N2 | 4 | yes | 1 | Diploma |
| E2 | Receipt Ingestion & Storage | BR-1 | 5 | yes | 1 | Diploma |
| E3 | Receipt Parsing & Extraction | BR-1 | 8 | no | 1 | Diploma |
| E4 | Multi-Photo Position Matching | BR-2 | 8 | yes | 1 | Diploma |
| E5 | Spend Categorization | BR-3 | 7 | no | 1 | Diploma |
| E6 | Monthly Budget Calculation | BR-4 | 7 | no | 1 | Diploma |
| E7 | Statistics, Comparison & Export | BR-5 | 6 | no | 1 | Diploma |
| E8 | Goals & AI Optimization Advice | BR-6 | 9 | yes | 1 | Diploma |
| E9 | Web Client Foundation | — | 6 | yes | 1 | Diploma |
| E10 | Security, Privacy & Observability | N1, N2, N3, N5 | 7 | no | 1 | Out of scope |
| E11 | Alternative Receipt Intake | — | 5 | yes | 2 | Diploma |
| E12 | Household & Shared Budgets | — | 7 | no | 2 | Diploma |
| E13 | Aggregated Purchase Analytics | — | 7 | no | 2 | Out of scope |
| E14 | B2B Export & Accounting Integrations | — | 6 | no | 2 | Out of scope |
| E15 | Receipt Accuracy & Trust | — | 4 | yes | 2 | Diploma |
| E16 | Personal Price History | — | 4 | yes | 2 | Diploma |

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

### F0.9 — Cloud deployment infrastructure (AWS)

*Requirements: —*

The application can be deployed to AWS from infrastructure-as-code rather than by hand. Targets AWS per ADR-0002. Not yet groomed into tasks: compute target (ECS/Fargate/EC2/App Runner), state backend, and which environments exist beyond local are real design decisions, made when this feature is picked up rather than guessed at while establishing repository layout.

### F0.10 — Identity, access and NFR acceptance criteria in the BRD

*Requirements: —*

Every existing BRD scenario opens with "Given the user is logged in", but the BRD itself never says what that means, and section 8's non-functional requirements (N1-N6) have EARS text with no Gherkin at all — both are real gaps F0.6.2's extraction correctly left untouched, since it could only move what the BRD already had. This closes them the same way BR-1..BR-6 were written: business-approved acceptance criteria first, so E1 (Identity & Account) and E10 (Security, Privacy & Observability) have something to build against instead of inventing it mid-epic.

- **F0.10.1** BR-7 Identity & Access, and NFR acceptance scenarios — Adds a new BR-7 section to the BRD (EARS requirements + Gherkin) covering registration, login, logout and session refresh; an admin role limited to service operation (no exception to N2 — an admin never reads another user's receipts or statistics); and sign-in via Google/Facebook OIDC coexisting with password auth, linked to an existing account only on a verified email match, with an explicit scenario rejecting a link attempt on an unverified email (the standard account-takeover vector for social login). Adds a Gherkin block to BRD section 8 for N1-N6, which today are EARS-only. Extends BRD section 9's data model with the User.role field and the identity-provider link entity BR-7 needs. Mirrors F0.6.2's own job for this new material: the scenarios land in tests/features/br7_identity_and_access/ and tests/features/nfr_cross_cutting/, wired via pytest-bdd and skipped pending E1/E10, and scripts/generate_brd_traceability.py regenerates brd-traceability.md to include them. Updates E1's `br:` list in backlog.yaml to add BR-7 alongside N2.

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

*Requirements: —*

Upload and AI-backed endpoints are the expensive ones; limit them per account and define the behaviour when a limit is hit.

**Demonstrated by:** Upload repeatedly past the limit and read the refusal on the upload screen — what the limit is and when it resets — rather than a bare 429.

### F10.7 — Account deletion and full data export

*Requirements: N6*

A user can export everything held about them and delete their account with all receipts and images, which section 11 makes a compliance expectation.

**Demonstrated by:** Export everything from Preferences and open the archive, then delete the account and confirm sign-in fails and the stored images are gone.

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

- **F11.2.3** Decide the inbound email provider — ADR choosing how inbound mail reaches the backend on AWS (ADR-0002) — SES receipt rules or a provider webhook — and fixing the limits a public intake address needs: message and attachment size, accepted attachment types, and a per-address rate.
- **F11.2.4** Per-user forwarding address — Give each user an unguessable forwarding address, stored with the user, that can be regenerated to stop spam reaching it; the old address stops accepting mail at once. Exposed to the user's own profile only (N2).
- **F11.2.1** Configure email ingestion webhook — Receive inbound mail from the chosen provider, resolve the forwarding address to its user, and accept only mail whose verified sender is one of that user's registered addresses. Rejected mail is logged and dropped, never stored.
- **F11.2.2** Implement email parsing and adapter — An email adapter implementing `ReceiptIngestionPort`: read the receipt from the HTML body or a PDF attachment through the existing parser, with the message id as the source reference. The receipt lands in the same review flow as a photo.
- **F11.2.5** Forwarding address and email receipts in the UI — Profile shows the forwarding address with copy and regenerate, and how to forward a receipt to it. Receipts marks email receipts and can be filtered by how they arrived. Checked at 375, 768 and 1280 px.

### F11.3 — Fiscal QR code intake

*Requirements: —* · *Blocked by: F11.1, F11.4*

Scanning the QR code printed on a fiscal receipt retrieves the itemised record from the fiscal service directly, producing exact item data with no extraction error and no confidence threshold to tune. Whether the target markets' QR codes lead to itemised data at all is for the F11.4 spike to establish; this feature waits for its answer.

**Demonstrated by:** On a phone, choose Upload, then Scan QR code, and point the camera at the code on a fiscal receipt: the receipt arrives itemised, marked "From QR code", without a step to check what was read.

- **F11.3.1** Implement fiscal service client and adapter — Create a client to fetch itemized data from the fiscal service using QR code content, and adapt it using `ReceiptIngestionPort`, with the fiscal number as the source reference. A code the service does not know is reported to the user, not guessed at.
- **F11.3.2** Scan a receipt's QR code in the upload flow — Add Scan QR code to Upload: the camera on a phone, an image of the code on desktop, and typing the code by hand when neither works. Mobile-first; checked at 375, 768 and 1280 px.

### F11.4 — National e-receipt service integration

*Requirements: —*

A feasibility spike followed by integration with the target market's e-receipt system (e-Paragon in Poland). The spike answers a question that affects the whole product: if receipts in this market become structured by law, extraction from photographs becomes the fallback path rather than the primary one. Produces an ADR before any code.

**Demonstrated by:** No screen of its own yet: proven by the ADR, which says for e-Paragony (PL) and єЧек (UA) whether a third party can read a user's receipts and how, and whether fiscal QR codes lead to itemised data. The integration tasks are written from that answer.

- **F11.4.1** Spike e-receipt system integration — Research integration feasibility with national e-receipt services and with fiscal QR codes in Poland and Ukraine. Produce an ADR with findings and architectural decisions, and the follow-up tasks for F11.3 and F11.4.

### F11.5 — Cross-channel duplicate detection

*Requirements: A14* · *Blocked by: F11.2*

One purchase that arrives twice through two channels is one receipt. BRD A14 compares merchant, date and total, which cannot tell a second channel's copy apart from a second visit to the same shop on the same day.

**Demonstrated by:** Photograph a purchase, then forward its e-receipt: instead of a second receipt, Receipts asks whether the email is the purchase already photographed, and the kept receipt lists both sources.

- **F11.5.1** Enhance duplicate detection with channel data — Update the duplicate detection algorithm to incorporate `channel` and `source_reference` to distinguish between cross-channel duplicates and same-day repeat purchases. A receipt arriving through the same source reference twice is always the same one.
- **F11.5.2** Confirm a cross-channel duplicate outside the upload flow — Email and QR receipts arrive without the upload wizard, so the A14 question is asked on Receipts: keep both, or merge into one receipt carrying both sources. Checked at 375, 768 and 1280 px.

---

## E12 — Household & Shared Budgets

**BRD sections:** — · **Phase:** 2 · **Scope:** Diploma

BRD section 4.2 places shared budgets out of scope and section 14 leaves the question open. Commercially they are what makes the product stick: a household that has agreed a shared budget does not churn the way one person tracking their own spending does. This is not a feature bolted on top — it replaces the single-owner model that N2, every repository and every access-control test are built around, which is why it needs a recorded decision before any schema changes.

### F12.1 — Ownership model decision

*Requirements: N2*

Whether a receipt is owned by a user who may share it, or by a household its members belong to. The choice constrains every repository already written, so it is decided and written up as an ADR before code changes.

### F12.2 — Household entity, membership and roles

*Requirements: —*

Households, the members in them, and what a member may do — who can edit a shared receipt, who can change the household budget, who can remove a member.

### F12.3 — Invitations and joining

*Requirements: —*

Inviting someone to a household and the states an invitation moves through, including an invitation to an address that has no account yet.

### F12.4 — Personal and shared visibility

*Requirements: —*

A member's receipts are not household property by default. Sharing is a decision made per receipt or per intake channel — the weekly grocery run is shared, the pharmacy visit is not — and the household's totals include only what was shared.

### F12.5 — Household budgets, statistics and goals

*Requirements: —*

BR-4, BR-5 and BR-6 computed over a household's combined shared data, including each member's contribution to the total, which is the number households actually argue over.

### F12.6 — Access control under shared ownership

*Requirements: N2*

The cross-user suite from F1.3 and F10.2 becomes a cross-household suite: membership grants access, removal revokes it immediately, and a personal receipt stays invisible to the rest of the household.

### F12.7 — Household interface

*Requirements: —*

Creating a household, managing members, choosing what is shared, and reading the household view of budget and statistics alongside the personal one.

---

## E13 — Aggregated Purchase Analytics

**BRD sections:** — · **Phase:** 2 · **Scope:** Out of scope

The item-level data BO-2 produces is something bank and card feeds structurally cannot supply: what was actually bought, not which shop was paid. Aggregated across many users and anonymised, that is a saleable market signal. This epic is written with its constraints first because the failure mode is legal rather than technical: no aggregate is produced without explicit consent, no figure is published for a cohort small enough to identify someone, and no raw personal purchase data leaves the system in any form.

### F13.1 — Explicit opt-in consent and withdrawal

*Requirements: —*

A separate, freely revocable consent — never bundled into terms of service — recording what was agreed to and when. Nothing else in this epic may touch a user's data without it, and withdrawal takes effect without the user having to ask twice.

### F13.2 — Product normalisation catalogue

*Requirements: —*

"MLEKO UHT 3,2% 1L" and "Mleko 3.2% 1l" have to become one canonical product. This is the technical core of the epic: without normalisation the aggregates are noise, and normalisation quality sets the ceiling on what the data is worth.

### F13.3 — Anonymisation and aggregation pipeline

*Requirements: —*

Pseudonymisation, deliberate coarsening of anything that narrows a person down, and aggregation — producing output in which no basket can be traced back to a household.

### F13.4 — Minimum cohort thresholds

*Requirements: —*

No figure is published for a cohort below a defined number of contributing users. A query that would breach the threshold returns nothing rather than a small-sample number, because a small sample is how anonymised data stops being anonymous.

### F13.5 — Separate analytics store

*Requirements: —*

Aggregates live outside the operational database, with no path from a business query back to a user's receipts. A boundary enforced by topology is worth more here than one enforced by review.

### F13.6 — Business insight API

*Requirements: —*

Price and basket trends per product and category for business consumers, versioned and metered, delivering only what the aggregation pipeline has already cleared.

### F13.7 — Transparency and deletion propagation

*Requirements: N3, N6*

A user can see what their data contributes, and withdrawing consent or deleting an account removes their contribution from future aggregates — the extension of N3 and N6 into a second data store.

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

### F16.2 — Price history of a product

*Requirements: —* · *Blocked by: F16.1*

The unit price of a product the user buys, over time and per shop, with how much it has risen or fallen, computed per kilogram or litre where the receipt gives a weight.

**Demonstrated by:** Open "Jogurt naturalny 330 ml" and read that it went from 4.99 to 5.49 at Biedronka since June, +10%, on a chart of every purchase.

- **F16.2.1** Unit price series per product — Endpoint returning each purchase's unit price, normalised by weight or volume where known, and the change over a period, from the user's own receipts only (N2).
- **F16.2.2** Product page with the price chart — A product page charting unit price per purchase, coloured by shop, with the change stated in words.

### F16.3 — Where it costs less

*Requirements: —* · *Blocked by: F16.2*

For products bought in more than one shop, which shop the user paid less in recently and by how much, only from their own receipts and only when both prices are recent enough to compare.

**Demonstrated by:** The products list says "cheaper at Lidl" next to five products, with the difference per unit, and none for a product last bought at Lidl a year ago.

- **F16.3.1** Shop comparison per product — Compare the latest unit prices per shop within a freshness window and report the cheaper shop and the difference.
- **F16.3.2** Cheaper-shop marks — Mark products with a cheaper shop in the products list and on the product page.

### F16.4 — Price signals in advice

*Requirements: F2, F4* · *Blocked by: F16.3, F8.5*

Price rises and cheaper shops become evidence advice can cite, so a recommendation can say "buy it at Lidl" with a saving computed from the user's own prices, not asserted.

**Demonstrated by:** Ask for advice on a spending ceiling and read "Buy Jogurt naturalny at Lidl: 0.80 less each, about 7 PLN a month at your rate".

- **F16.4.1** Price evidence in goal analysis — Add price rises and cheaper shops for the goal's products to the analysis the advice model reads.
- **F16.4.2** Saving from a shop switch — Compute the monthly saving of buying a product in the cheaper shop from the price gap and the user's purchase rate, the same way projected impact is computed for F8.5.

