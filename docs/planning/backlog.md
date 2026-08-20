# Delivery backlog

> Generated from [`backlog.yaml`](backlog.yaml) by `scripts/backlog_sync.py render`.
> Edit the YAML, not this file.

15 epics · 106 features · 58 tasks written so far.

11 epics are phase 1 — the BRD scope, delivered before launch. 4 are phase 2: commercial scope that is planned but deliberately not started until phase 1 is complete.

| Epic | Title | BRD | Features | Groomed | Phase |
|---|---|---|---|---|---|
| E0 | Foundation & Delivery Platform | — | 10 | yes | 1 |
| E1 | Identity & Account | BR-7, N2 | 5 | yes | 1 |
| E2 | Receipt Ingestion & Storage | BR-1 | 6 | no | 1 |
| E3 | Receipt Parsing & Extraction | BR-1 | 7 | no | 1 |
| E4 | Multi-Photo Position Matching | BR-2 | 7 | no | 1 |
| E5 | Spend Categorization | BR-3 | 8 | no | 1 |
| E6 | Monthly Budget Calculation | BR-4 | 7 | no | 1 |
| E7 | Statistics, Comparison & Export | BR-5 | 7 | no | 1 |
| E8 | Goals & AI Optimization Advice | BR-6 | 10 | no | 1 |
| E9 | Web Client Foundation | — | 6 | yes | 1 |
| E10 | Security, Privacy & Observability | N1, N2, N3, N5 | 7 | no | 1 |
| E11 | Alternative Receipt Intake | — | 6 | no | 2 |
| E12 | Household & Shared Budgets | — | 7 | no | 2 |
| E13 | Aggregated Purchase Analytics | — | 7 | no | 2 |
| E14 | B2B Export & Accounting Integrations | — | 6 | no | 2 |

---

## E0 — Foundation & Delivery Platform

**BRD sections:** — · **Phase:** 1

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
- **F0.4.2** Task runner targets for the common workflows — up, down, migrate, test, lint, typecheck. Both languages behind the same interface so nobody memorises two toolchains. A `seed` target lands with the seed script itself in F5.8, once there are entities to seed.
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

**BRD sections:** BR-7, N2 · **Phase:** 1

Every BRD scenario begins with "Given the user is logged in", and N2 forbids one user's data from reaching another. This epic establishes authentication, session handling, the user profile fields from the BRD data model, and the scoping guarantee that all later epics depend on. Full stack: the login, registration and logout screens and the authenticated route table live here with the endpoints they call (F1.5), not in E9 — E9 owns only the frontend groundwork that has no domain dependency.

### F1.1 — Registration and login

*Requirements: —*

A person can create an account with an email and password and authenticate with it.

- **F1.1.1** User table migration and SQLAlchemy model — Implements the User entity from BRD section 9: user_id, email, password_hash, currency, budget_limit. The goal relationship is added by epic E8; currency and budget_limit land here because they are account-level settings.
- **F1.1.2** Password hashing and strength policy — Argon2id with documented parameters, a minimum-length policy, and a check against a common-password list. Hashing cost must be configurable per environment so tests stay fast without weakening production.
- **F1.1.3** POST /auth/register endpoint — Validates the payload, rejects duplicate emails without revealing whether an address is registered, and returns the created account with a session.
- **F1.1.4** POST /auth/login endpoint — Constant-time credential verification, a uniform error for both unknown email and wrong password, and throttling on repeated failures.
- **F1.1.5** Acceptance tests for registration and login — Covers the happy path, duplicate registration, wrong password, and the guarantee that responses do not leak account existence.

### F1.2 — Session and token management

*Requirements: —*

An authenticated session persists across requests, can be refreshed, and can be revoked on logout.

- **F1.2.1** Access token issuance — Short-lived JWT carrying the user id and issued-at, signed with a key from settings. Claims kept minimal — no financial data in the token.
- **F1.2.2** Refresh token storage and rotation — Server-side refresh tokens with rotation on use and reuse detection that revokes the whole family, so a stolen refresh token cannot be replayed.
- **F1.2.3** Refresh and logout endpoints — POST /auth/refresh exchanging a valid refresh token, POST /auth/logout revoking the current session.
- **F1.2.4** Current-user dependency — A FastAPI dependency resolving the authenticated user, returning 401 with the standard error envelope when absent or expired. This is the single entry point every protected route uses.

### F1.3 — Per-user data scoping guarantee

*Requirements: —*

Satisfies BRD N2 structurally rather than by convention: it must be difficult to write a query that returns another user's data.

- **F1.3.1** Request-scoped user context — The authenticated user id is available to the persistence layer for the duration of the request without being threaded manually through every function signature.
- **F1.3.2** Ownership-enforcing repository base class — A base repository that applies the user_id filter automatically for all user-owned entities. Bypassing it requires an explicit, greppable escape hatch.
- **F1.3.3** Cross-user access test suite — For every user-owned resource, assert that user B receives 404 rather than 403 for user A's records, so existence is not disclosed. This suite is extended by each later epic that introduces a new owned entity.

### F1.4 — User profile and preferences

*Requirements: —* · *Blocked by: F1.1, F9.4*

A user can set the account currency and an optional monthly budget limit, which BRD D7 uses to express spend as a percentage of target.

- **F1.4.1** GET and PATCH /me endpoints — Read and partially update the profile. Changing budget_limit must not retroactively rewrite finalised monthly snapshots — it affects presentation only.
- **F1.4.2** Currency validation and the single-currency assumption — ISO 4217 validation, and an explicit guard rejecting a currency change once receipts exist, since BRD section 4.2 puts conversion out of scope.
- **F1.4.3** Profile screen — Displays and edits currency and monthly budget limit, backed by a MobX store following the conventions set in epic E9.

### F1.5 — Authentication flows and protected routing

*Requirements: —* · *Blocked by: F1.1, F1.2, F9.3, F9.4*

The screens that make this epic's endpoints usable and testable without curl: login, registration and logout, token storage, transparent refresh on 401 without losing the user's in-flight action, and the authenticated-versus-public route table with its redirect on expiry. Held here rather than in E9 because it is the frontend half of this epic's own capability — separating the two put a working UI eight epics away from the API it exercises. Not yet groomed into tasks: the storage strategy and guard shape follow from F1.2's session model, which does not exist yet.

---

## E2 — Receipt Ingestion & Storage

**BRD sections:** BR-1 · **Phase:** 1

Accepting receipt photos: format validation, the two upload modes with their photo-count and size limits, durable encrypted storage of the originals, and asynchronous processing status. Covers BRD A1 through A8 and the storage half of A12.

### F2.1 — Upload endpoint and file format validation

*Requirements: A1, A2*

Submitted files are validated as JPEG, PNG, HEIC or PDF-scan by content inspection rather than by extension, and rejections state the accepted formats.

### F2.2 — Single-receipt upload mode

*Requirements: A3, A4, A7, A8*

One receipt captured across up to 10 photos totalling at most 50 MB, with limit violations rejected and explained.

### F2.3 — Multiple-receipts upload mode

*Requirements: A3, A5, A6, A7, A8*

Several distinct receipts in one session, one upload line each, with the 10-photo and 50 MB limits applied independently per line so one bad line cannot fail the others.

### F2.4 — Encrypted object storage for receipt images

*Requirements: A12, N1*

Original images are stored in object storage encrypted at rest, referenced from the receipt record, and retrievable only by their owner via time-limited URLs.

### F2.5 — Asynchronous ingestion pipeline and status tracking

*Requirements: N4*

Upload returns immediately with a tracking handle while parsing proceeds in the background, so the 10-second target of N4 is a processing budget rather than a request timeout.

### F2.6 — Upload user interface

*Requirements: A3, A4, A5, A6, A7, A8* · *Blocked by: F2.2, F2.3, F1.5, F9.4*

Mode selection, adding upload lines, per-line photo previews, and client-side limit feedback before bytes are sent.

---

## E3 — Receipt Parsing & Extraction

**BRD sections:** BR-1 · **Phase:** 1

Turning a validated photo into a structured receipt: field extraction, confidence handling, manual-review flagging, duplicate detection and persistence with provenance. Covers BRD A9 through A15.

### F3.1 — Vision extraction provider integration

*Requirements: A9*

A versioned, testable adapter over the Claude vision API that turns receipt images into structured output, with the prompt and schema under source control.

### F3.2 — Extraction schema and validation

*Requirements: A9*

Merchant, transaction date, transaction time, line items (name, quantity, unit price, total price) and total amount, validated for internal arithmetic consistency.

### F3.3 — Confidence scoring and low-confidence flagging

*Requirements: A10*

Per-field confidence recorded, and fields below threshold marked "low confidence" and surfaced for confirmation instead of being silently accepted.

### F3.4 — Manual-review status for missing critical fields

*Requirements: A11*

A receipt without an extractable total or date is marked "requires manual review" and excluded from all automated budget calculation until a human resolves it.

### F3.5 — Receipt persistence with provenance

*Requirements: A12, A13, A15*

Header, line items and image reference stored under a unique receipt id, owned by the submitting account, stamped with processing time and parser version.

### F3.6 — Duplicate receipt detection

*Requirements: A14*

A receipt matching an existing one on merchant, date and total prompts the user to confirm before storing, rather than being silently accepted or silently dropped.

### F3.7 — Receipt review and correction interface

*Requirements: A10, A11, A14* · *Blocked by: F3.3, F3.4, F1.5, F9.4*

Side-by-side original photo and extracted data, with low-confidence fields highlighted for confirmation and the manual-review queue reachable in one click.

---

## E4 — Multi-Photo Position Matching

**BRD sections:** BR-2 · **Phase:** 1

Recognising that a line item appearing on two overlapping photos of one long receipt is the same purchase, so it is counted once — while never collapsing genuinely repeated purchases made on different receipts. Covers BRD B1 through B9.

### F4.1 — Independent per-photo extraction for comparison

*Requirements: B1*

Each photo is parsed on its own before any comparison, so a match decision is never an artefact of parsing the two images together.

### F4.2 — Position comparison rules

*Requirements: B2, B3, B4*

Item name, unit price, quantity and total price must all match exactly for a pair to be "same position"; any difference makes it "different position".

### F4.3 — Same-receipt scoping guard

*Requirements: B5, B9*

Comparison runs only between photos of one physical receipt. Identical items on two distinct transactions are two purchases, never a duplicate — this is the requirement most likely to be violated by a naive deduplication implementation.

### F4.4 — Comparison failure handling

*Requirements: B6*

If either photo failed to parse, return "comparison not possible" with the reason instead of guessing.

### F4.5 — Manual override and correction capture

*Requirements: B7, B8*

A user can overturn any automatic determination, and the correction is stored as labelled data for future evaluation and tuning.

### F4.6 — Deduplicated receipt assembly

*Requirements: B3*

Merge the per-photo extractions of one receipt into a single item list where matched positions appear exactly once, and reconcile the result against the printed total.

### F4.7 — Match review interface

*Requirements: B7* · *Blocked by: F4.2, F4.5, F1.5, F9.4*

Show detected overlaps between photos with the evidence, and let the user flip any decision.

---

## E5 — Spend Categorization

**BRD sections:** BR-3 · **Phase:** 1

Classifying every line item into a spending category, with a confidence-gated fallback, user correction that the system learns from, and user-defined categories. Covers BRD C1 through C7.

### F5.1 — Default category taxonomy

*Requirements: C1, C2*

Seeded default categories (Groceries, Dining, Transport, Utilities, Health, Entertainment, Other) plus a guaranteed Uncategorized fallback, modelled so custom user categories coexist with defaults.

### F5.2 — Automatic item categorization

*Requirements: C1*

Each parsed line item receives a category and a recorded confidence score.

### F5.3 — Confidence threshold and Uncategorized fallback

*Requirements: C2, C3*

Below-threshold classifications become Uncategorized and are flagged for review rather than guessed at.

### F5.4 — Manual category reassignment

*Requirements: C4*

Any line item's category can be changed by its owner, and the override is recorded as manual so later automatic passes do not overwrite it.

### F5.5 — Learning from corrections

*Requirements: C5*

A correction creates a rule applying to future items with the same or highly similar name from the same merchant, which requires a defined similarity measure and a precedence order against automatic classification.

### F5.6 — User-defined custom categories

*Requirements: C6, C7*

Users can create their own categories, immediately available for both manual and automatic assignment, including the behaviour when a category in use is renamed or deleted.

### F5.7 — Categorization review interface

*Requirements: C3, C4, C6* · *Blocked by: F5.3, F5.4, F1.5, F9.4*

A review queue for flagged items and inline category editing wherever line items are displayed.

### F5.8 — Seed script for local sample data

*Requirements: —* · *Blocked by: F1.1, F3.5, F5.1*

A demo user with a handful of categorised receipts spanning two months, plus the `seed` task-runner target that invokes it — enough to exercise the monthly-budget and statistics epics without uploading photos. Lands here, at the end of E5, because this is the first point where every entity it writes exists: User (F1.1), receipt and line items (F3.5) and categories (F5.1). It was originally planned in E0's local development environment, where none of those had been built yet.

---

## E6 — Monthly Budget Calculation

**BRD sections:** BR-4 · **Phase:** 1

Aggregating receipts into monthly totals by transaction date, distinguishing a month-to-date figure from a finalised one, excluding flagged receipts transparently, and recalculating when history changes. Covers BRD D1 through D7.

### F6.1 — Monthly aggregation engine

*Requirements: D1, D2*

Sum line-item totals across all receipts whose transaction date — not upload date — falls in the month, which makes back-dated uploads behave correctly.

### F6.2 — Transparent exclusion of receipts under review

*Requirements: D3*

Receipts marked "requires manual review" are excluded from the total, and the summary states how many were excluded and their value, so the number is never quietly wrong.

### F6.3 — Month-to-date versus finalised presentation

*Requirements: D4*

An in-progress month is labelled incomplete wherever it appears, so a partial figure is never mistaken for a full one.

### F6.4 — Monthly snapshot generation

*Requirements: D5*

When a month completes, persist a finalised snapshot (the MonthlySnapshot entity), including how the transition is triggered across user time zones.

### F6.5 — Recalculation on receipt change

*Requirements: D6, N3*

Adding, editing or deleting a receipt in a closed month recalculates and updates the stored snapshot, with the recalculation reflected in the same session.

### F6.6 — Budget limit and percentage of target

*Requirements: D7*

Where a monthly limit is set, express current spend as a percentage of it, including the over-100% case.

### F6.7 — Budget dashboard

*Requirements: D1, D4, D7* · *Blocked by: F6.3, F6.6, F1.5, F9.4*

The landing view: current month-to-date spend, progress against limit, excluded-receipt notice, and month switching.

---

## E7 — Statistics, Comparison & Export

**BRD sections:** BR-5 · **Phase:** 1

Category-level insight over arbitrary date ranges, period-over-period comparison, honest empty states, chart-ready output, and data export. Covers BRD E1 through E6 and N6.

### F7.1 — Category statistics engine

*Requirements: E1, E4*

Total spend, share of overall spend and transaction count per category, ranked from highest to lowest by default.

### F7.2 — Arbitrary date-range support

*Requirements: E2*

Statistics for any start and end date, not only calendar months, with inclusive boundary semantics defined once and applied everywhere.

### F7.3 — Period-over-period comparison

*Requirements: E3*

Absolute and percentage change per category between two periods, including categories present in only one of them and the division-by-zero case.

### F7.4 — Empty-period handling

*Requirements: E5*

A range with no receipts returns an explicit "no data" result rather than a zero-filled report that reads like real information.

### F7.5 — Chart-ready output

*Requirements: E6*

A response shape the client can render directly, so presentation logic does not re-derive aggregates.

### F7.6 — Data export

*Requirements: N6*

CSV and JSON export of the user's receipts, line items and statistics, generated asynchronously for large histories.

### F7.7 — Statistics and charts interface

*Requirements: E1, E3, E6* · *Blocked by: F7.3, F7.5, F1.5, F9.4*

Ranked category breakdown, range picker, comparison view and the export action.

---

## E8 — Goals & AI Optimization Advice

**BRD sections:** BR-6 · **Phase:** 1

The product's differentiator: a user states a financial or lifestyle goal and receives specific, evidence-based, quantified recommendations tied to their own purchase history, with proactive warnings and a feedback loop. Covers BRD F1 through F9.

### F8.1 — Goal definition and storage

*Requirements: F1*

Model both financial goals (savings target, category reduction, overall ceiling) and lifestyle goals (lose weight, save for a car) in one schema without collapsing the distinction that F9 depends on.

### F8.2 — Lifestyle goal to spending mapping

*Requirements: F9*

Translate a non-financial goal into the relevant categories and recurring items before any advice is generated, since the rest of the pipeline reasons over spend.

### F8.3 — Spend analysis for advice

*Requirements: F2*

Identify highest-spend categories, largest recent increases, and recurring positions most relevant to the stated goal — the evidence every recommendation must cite.

### F8.4 — Recommendation generation

*Requirements: F3*

Produce specific, actionable recommendations naming a category or an individual recurring item. Constraint 11.3 rules out generic financial tips, so genericness is a defect to be tested for, not a style preference.

### F8.5 — Projected impact quantification

*Requirements: F4*

Every recommendation states its expected effect on the goal, computed from the user's actual history rather than asserted by the model.

### F8.6 — Insufficient-data guard

*Requirements: F5*

Below a configured minimum of history, say more data is needed instead of emitting a low-confidence recommendation.

### F8.7 — On-track progress reporting

*Requirements: F6*

When pace meets the goal, report positive progress and explicitly suppress unnecessary cuts.

### F8.8 — Proactive at-risk warnings

*Requirements: F7*

Detect mid-month that projected spend will miss the goal and surface a warning with at least one corrective recommendation before the month ends — this requires scheduled evaluation and a delivery channel, not just a request handler.

### F8.9 — Recommendation feedback loop

*Requirements: F8*

Capture "not followed" and "not helpful" feedback and deprioritise similar recommendations in later generations.

### F8.10 — Goals and advice interface

*Requirements: F1, F3, F6, F7, F8* · *Blocked by: F8.4, F8.7, F1.5, F9.4*

Goal setup, progress display, the advice feed with projected impact, and the feedback controls that make F8 possible.

---

## E9 — Web Client Foundation

**BRD sections:** — · **Phase:** 1

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

The static frame every screen renders inside: header, navigation, responsive content container, and the router mounted with public routes only. Deliberately excludes the authenticated route table, the auth guard and the expiry redirect — those need F1's session model, and they ship with it in F1.5. What remains here has no domain dependency, so it can be built before any endpoint exists.

### F9.6 — Component primitives and design tokens

*Requirements: —*

Buttons, forms, tables, modals, currency and date formatting bound to the account currency, and the token set they draw from.

- **F9.6.1** Color-token system ported from budget-checker — Tailwind v4 with a `@theme` layer over semantic CSS custom properties (--color-background, --color-primary, etc.) in src/shared/styles/colors.css, light values on :root and dark overrides on .dark. One source of truth per DS-1: components reference tokens (bg-primary, text-foreground), never a raw hex.
- **F9.6.2** Responsive breakpoint tokens (mobile / tablet / desktop) — Named breakpoint tokens in src/shared/styles/breakpoints.css and a mobile-first convention: base styles target mobile, md:/lg: Tailwind variants layer up tablet and desktop. No shared component ships a fixed pixel width.
- **F9.6.3** Reusable primitive component library — src/shared/components/ — Button, Input, Select, Modal, Table, Card — each typed, each built only from the tokens above. A feature screen composes these instead of hand-rolling markup for a UI role that already exists.
- **F9.6.4** Shared layout primitives and style utilities — src/shared/styles/ spacing and typography scale plus layout primitives (Stack, Grid, a responsive Container) reused across breakpoints, so a screen composes layout instead of hand-rolling flexbox per page.

### F9.7 — Loading, empty and error state conventions

*Requirements: —*

One documented treatment for each, so the honest empty states E5 and F5 require are consistent rather than per-screen improvisations. Not yet groomed into tasks: easiest to standardise once a couple of real feature screens exist to generalise from.

---

## E10 — Security, Privacy & Observability

**BRD sections:** N1, N2, N3, N5 · **Phase:** 1

The cross-cutting non-functional requirements from BRD section 8 and the constraints in section 11, given their own epic so they are scheduled work rather than assumed work.

### F10.1 — Encryption at rest for images and extracted data

*Requirements: N1*

Receipt images and the extracted financial fields are encrypted at rest, with a documented key management and rotation approach.

### F10.2 — Access control verification

*Requirements: N2*

An automated suite covering every user-owned endpoint, extending the base suite from F1.3 as each epic adds resources.

### F10.3 — Receipt deletion and cascade

*Requirements: N3*

Deleting a receipt removes it from budget and statistics results within the same session, including its effect on any finalised snapshot.

### F10.4 — Classification decision audit log

*Requirements: N5*

Every automatic category assignment and position-match decision logged with its confidence score, supporting both auditing and the tuning that C5 and B8 imply.

### F10.5 — Structured logging, metrics and tracing

*Requirements: —*

Correlated request logging with financial values redacted, plus the latency metrics needed to prove the N4 target is met.

### F10.6 — Rate limiting and abuse protection

*Requirements: —*

Upload and AI-backed endpoints are the expensive ones; limit them per account and define the behaviour when a limit is hit.

### F10.7 — Account deletion and full data export

*Requirements: N6*

A user can export everything held about them and delete their account with all receipts and images, which section 11 makes a compliance expectation.

---

## E11 — Alternative Receipt Intake

**BRD sections:** — · **Phase:** 2

BRD section 10 assumes every receipt arrives as a photograph. That assumption is the product's largest retention risk: photographing receipts is effort the user has to repeat every week, and repeated effort is what stops budgeting apps being opened after the second week. This epic adds intake that costs the user nothing — e-receipts arriving by email, the fiscal QR code printed on the receipt, and national e-receipt services — behind the same ingestion pipeline, so the channel changes only how a receipt arrives and nothing downstream of it.

### F11.1 — Intake channel abstraction

*Requirements: A12, A15*

One ingestion port with an adapter per channel, so adding a channel does not touch parsing, categorisation or budget calculation. Every receipt records the channel it arrived through and the source reference, because a support question about a wrong figure starts with where the data came from.

### F11.2 — Email receipt ingestion

*Requirements: —*

A per-user forwarding address that accepts electronic receipts, extracting items from HTML bodies and PDF attachments. Sender verification matters here: an intake address is a public endpoint that writes to a user's financial record.

### F11.3 — Fiscal QR code intake

*Requirements: —*

Scanning the QR code printed on a fiscal receipt retrieves the itemised record from the fiscal service directly, producing exact item data with no extraction error and no confidence threshold to tune.

### F11.4 — National e-receipt service integration

*Requirements: —*

A feasibility spike followed by integration with the target market's e-receipt system (e-Paragon in Poland). The spike answers a question that affects the whole product: if receipts in this market become structured by law, extraction from photographs becomes the fallback path rather than the primary one. Produces an ADR before any code.

### F11.5 — Cross-channel duplicate detection

*Requirements: A14*

One purchase that arrives twice through two channels is one receipt. BRD A14 compares merchant, date and total, which cannot tell a second channel's copy apart from a second visit to the same shop on the same day.

### F11.6 — Intake settings interface

*Requirements: —*

The user can see their forwarding address, which channels are connected, and what arrived through each of them.

---

## E12 — Household & Shared Budgets

**BRD sections:** — · **Phase:** 2

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

**BRD sections:** — · **Phase:** 2

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

**BRD sections:** — · **Phase:** 2

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

