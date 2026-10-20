# Architecture overview

How the system is put together and why. Read this before changing structure; read
[`domain-model.md`](domain-model.md) before changing business rules.

**Keep this document current.** When a change alters the component boundaries, a data
flow, or an integration point, updating this file is part of that change, not a
follow-up. A stale architecture document is worse than none, because it is trusted.

## Shape

A single-page React client talks to one FastAPI service over HTTP. The service owns
all business logic and is the only thing that touches PostgreSQL, object storage or
the Claude API.

```
React + MobX  ──HTTP/JSON──►  FastAPI  ──►  PostgreSQL   (receipts, items, budgets)
                                    ├──►  Object store  (receipt images, encrypted)
                                    └──►  LLM API     (Gemini/Claude/OpenAI via litellm)
```

There is no separate worker service yet. Receipt processing runs as a background task
inside the API process. That is a deliberate simplification for the current scale, and
the first thing to revisit if parsing throughput becomes a constraint — the ingestion
pipeline is already written around a job record rather than a request/response call, so
extracting it into its own process is a deployment change, not a rewrite.

## Layers inside the API

Requests flow strictly downward. A layer may call the one beneath it and never the one
above.

| Layer | Responsibility | Must not |
|---|---|---|
| **Router** | HTTP concerns: parse request, check auth, serialise response | Contain business rules or build queries |
| **Service** | Business rules, orchestration, transactions | Know about HTTP status codes or SQL |
| **Repository** | Data access, ownership filtering | Make business decisions |
| **Agent** | Provider-agnostic LLM capabilities (wrapped via `litellm`) | Connect to the database or define HTTP routes |
| **Port** | Protocol describing an external dependency | Reference a concrete vendor SDK |

Services depend on ports, not implementations. `ReceiptParser`, `ItemCategoriser`,
`GoalMapper` and `AdviceGenerator` are protocols; the Agent-backed classes implementing them
are wired in by FastAPI `Depends` (`get_item_categoriser`, `get_goal_mapper`,
`get_advice_generator`), all built on one LLM client from `app/agent/factory.py`. This is what allows the BDD acceptance suite to run the real
business logic against stub implementations with no network access.

How a receipt arrives is a port of its own, `ReceiptIngestionPort` (`app/ports/ingestion.py`,
F11.1): one adapter per intake channel turns what that channel receives into one extraction,
and categorisation, review and budgeting run on it unchanged. Photo upload and email are
the channels so far (`app/adapters/photo_ingestion.py`, `app/adapters/email_ingestion.py`); every receipt records its `channel` — carried on the upload job for receipts that go through the wizard (F11.1.4) — and
an optional `source_reference`. The photo adapter writes each image under
`receipts/{user_id}/` (`receipt_object_name`, in `app/ports/storage.py`), the prefix that
makes another user's photo impossible to name (N2).

Email arrives from outside (F11.2, ADR-0013): a relay — App Engine's inbound mail in
production, the `mail-relay` compose service locally — POSTs each raw message to
`/api/v1/webhooks/inbound-email` with a shared secret. `InboundEmailService` decides
whether it may become a receipt; `ReceiptService.store_from_channel` reads and stores it in
the background, with the same categorisation as an upload.

Mail goes out the same way in reverse (F17.8, ADR-0019): services write a `Letter`
(`app/domain/letters.py`, in the reader's language) and `Mailer` hands it to
`EmailSenderPort` in a background task, retrying. In production the adapter posts it to
the App Engine relay's `/send`, which calls the Mail API; locally it is written to the
log. Links in letters are signed tokens bound to the state they change
(`AccountService`), so they work once and are never accepted as a session. The Help page's
contact form (F17.10) goes out the same way, to the support mailbox (F22.1.2) with the sender as
Reply-To, so no address is published and the service keeps nothing of it.

The user's data rights (F17.9, ADR-0020) lean on the schema rather than on lists kept by
hand: deleting an account deletes the user row and every table cascades from it
(`AccountClosureService`), then removes the files by prefix through
`StoragePort.delete_prefix`; "download everything" is an export job of kind `account`
(`app/services/data_export.py`) that writes every row of every table with a `user_id`
column, so a table added later is exported and deleted without anyone remembering to.
The service measures its own use rather than through a third party (F17.3):
`ActivityService` writes an `activity_events` row with the request's other changes,
public pages report a view to `/api/v1/analytics/views` (counted, not stored per
visitor), and `UsageReportService` builds the admin dashboard from those and from the
users, upload and receipt tables. Old activity is pruned when an instance starts.

The admin console (F18.6, ADR-0021) is one router, `/api/v1/admin`, behind two
dependencies: `get_admin_user` (an admin, with a second-factor session where the
deployment requires it) and `get_super_admin` (appointing admins, reading the log).
`AdminService` reads accounts through `AdminUsersRepository` — facts and activity, never a
receipt — and writes every action to `admin_actions`. Two-factor sign-in lives in
`TwoFactorService`; `AuthService.login` answers a challenge instead of a session when it is
on, and the session's second factor travels as the access token's `sf` claim and the
refresh token's flag. The plan in force is read by `PlanService` from `plan_grants`
(`app/domain/plans.py`), and `QuotaService` takes its limit from it (F18.4).

Retention is the bucket's: lifecycle rules in `infra/terraform/storage.tf` delete photos
after 90 days and exports after 7; `app/domain/retention.py` only tells the screens when.

Whatever the channel, a receipt is checked against the user's stored ones before it is
stored (F11.5, ADR-0015): by its fiscal identity (`app/domain/fiscal_identity.py`), read
off the receipt by the model, which recognises a copy exactly, and otherwise by merchant,
date and total, which only flags it for the user.

A receipt paid in another currency is converted into the account's when it is stored
(F11.7, ADR-0016) through `ExchangeRatePort` (`app/ports/exchange_rates.py`): the National
Bank of Poland's rates, the ECB's (Frankfurter) as fallback (`app/adapters/exchange_rates.py`),
each rate cached in the `exchange_rates` table by pair and date. The wizard is shown the
rate before storing; budget and statistics only ever see the account's currency.

Products (F16.1) match the user's purchase lines across receipts and shops
(`app/services/product.py`, behind `/api/v1/products`). A printed name is reduced to a key
— words and package size — by `app/domain/products.py`; a known key or an abbreviation of
one of the same size is matched by rule, and only names merely alike go to the model, in
one batch, through `ProductMatcherPort` (`app/ports/product_matching.py`). Matching runs
when the products list is asked for, so receipts stored before products existed join too.
Every way a product is printed is kept as an alias, so the user's merges and splits hold
for later receipts.
`GET /api/v1/products/explore` answers for a selection of products and a period: totals,
month by month, each purchase's price, and prices per shop (`app/domain/purchases.py`);
selections can be saved under a name (`/api/v1/products/selections`).

Trips (F20.1) live in `app/services/trip.py` behind `/api/v1/trips`. Which receipts a trip
holds is worked out when asked — by date, or by the user's choice stored on the receipt —
so no intake path has to know about trips; the upload wizard's commit only records the
user's answer for a receipt dated within one (`CommitJobRequest.trips`). The same placing
rule exists twice, in SQL for figures (`on_trip`, `awaiting_answer`) and in Python for
lists (`app.domain.trips.place`), and the two must change together. A business trip's per diem
(F20.4) is a pure calculation in `app/domain/per_diem.py` over the times stored on the trip,
with the regulation's rates in `per_diem_rates_pl.json` beside it (ADR-0018). A business trip's
settlement (F20.5) is one more export kind (`trip`) through the F7.6 export jobs, written by
`app/services/settlement.py` as PDF (fpdf2, with the DejaVu fonts in `app/assets/fonts` for
Polish and Ukrainian, and the receipts' photos read from object storage) or CSV. Every budget figure reads receipts through one
rule, `counted_in_budget()` in `app/repository/receipt.py`: parsed, and not on a business
trip.
A receipt's kind of expense (F20.2) is one more field of the reading every intake path
already makes (`ExtractedReceipt.expense_kind`), so it costs no extra model call and is
there whichever trip the receipt later turns out to be on.

Households (E12, ADR-0017) live in `app/services/household.py` behind `/api/v1/household`.
They have no `user_id`, so `HouseholdRepository` does not use the ownership filter: every
lookup starts from the caller's own membership row, which is what keeps one household out
of another's reach (N2) — except joining, which names a household by the 128-bit code in
its invite link (F12.3). Looking at and using invite links share one per-IP limit, since
the limiter keys routes by URL and every code is a different one. Receipts are untouched
by membership. Reading them (F12.4) goes through `HouseholdReaders`
(`app/repository/receipt.py`): built from the caller's membership on each request, it is
the one SQL condition — a member's own receipts and the others' that are not private —
used by `GET /receipts?scope=household` and by opening a receipt that is not the
caller's. Every write keeps the plain ownership filter, so another member's receipt is
not found for editing, deleting, recategorising or privacy. Photos stay under their
owner's storage prefix; `GET /receipts/images/{file_id}` signs one under another
member's prefix only when `HouseholdReaders` finds it on a receipt the caller may read, so
a private receipt's photo, or a stranger's, is never found.

The household's month and statistics (F12.5) come from `HouseholdBudgetService`
(`app/services/household_budget.py`) over `HouseholdSpendRepository`, which returns sums
only: per member, shared and private apart, and per category over shared receipts. No
query in it returns a private receipt's merchant, items, category or date.

Money a household shares (F12.8, ADR-0023) — incomes, regular incomes and regular bills —
is read and changed through `SharedWithHousehold` (`app/repository/shared.py`), the one
place the ownership filter is widened: a row the caller wrote, or one whose `household_id`
is the household the caller belongs to now. `IncomeService.sharing` says whose each row is;
leaving or removal (`HouseholdService._take_back`) returns a
member's shared rows to them in the same transaction.

Roles (F12.10): the membership row says `owner`, `member` (an adult) or `child`. A child
is refused every shared write in one place, `refuse_child` in `app/services/household.py`,
which `IncomeService` calls when a row is or would become shared, and which the household
budget and a receipt's privacy call too.

The assistant (F21.1, ADR-0025) lives in `app/services/assistant.py` behind
`/api/v1/assistant`. An `AssistantPort` (`app/adapters/assistant_agent.py` over the LiteLLM
agent) answers each message, running read tools at once and returning write tools only as
proposals. `Toolbox` (`app/services/assistant_tools.py`) turns a proposal into a card and,
when the user approves it, saves it through the service its screen uses. Questions about
spending (F21.4) are read tools in `app/services/assistant_reads.py` over the screens' own
queries (`StatisticsService`, `ReceiptRepository`, `ProductService`); each leaves an answer
card — the Spending chart and a link to the screen with the same filters — shown below the
answer, never approved and never read back to the model. Conversations and
their messages are the user's rows, deleted and exported with the account.

What the family buys line by line (F12.11) is `HouseholdSpendRepository.shared_lines`
— shared receipts' lines only — read by `app/domain/family_lines.py` into products bought
twice, who buys what, and the swaps a stretch goal's check names (`GoalCheckService`).

Accounts (F23.15, ADR-0024) live in `app/services/money_accounts.py` behind
`/api/v1/accounts`. `AccountService._entries` turns every sum that reaches or leaves an
account the caller sees — income entries, regular incomes, bills and transfers read from
their rules, moves, tax payments and each member's purchases by day — into one list of
`Entry` lines (`app/domain/accounts.py`); balances, histories, "To check" and Home's
balance (`BalanceService`) are all sums over that one list, so they cannot disagree.
Rules are never posted ahead: a month's occurrence is read from the rule unless an income
(`source_id`) or a move (`bill_id`, `rule_id`) stands in for it. Shared accounts use the
household widening above; moves and monthly transfers are visible through the accounts
they touch (`app/repository/money_accounts.py`).

Accounts are optional (F23.21, ADR-0027). `IncomeService._place` puts a bill or a tax
payment on the named card, the purchase card, or none; `IncomeService._land` puts income on
a card always, making it from the request's `new_card` when there is none, else refusing
with `needs_card`. Regular rules are monthly on a `day` or weekly on a `weekday`
(`Recurring.days_in` in `app/domain/income.py`); every consumer — the ledger, the month's
income, the household budget, the balance — reads a rule's days and amounts from it. The
month's bills (`IncomeService.bills_in`, `bills_between`) count against the budget in
`BudgetService.month_summary` and appear beside the categories in the statistics response.

These rules are held together by one suite, `backend/tests/security/test_cross_household_access.py`
(F12.6): it builds a household with an owner, a member, a removed member and a stranger
elsewhere, then walks every read that reaches or adds up another member's receipts and
every write on a receipt as each of them. No response may carry the private receipt's
details, the removed member and the stranger read nothing, and every write stays the
owner's. A new household-aware route belongs in its tables.

### Errors crossing the API boundary

A service or repository that needs to fail the request raises an `app.errors.AppError`
subclass (`NotFoundError`, `PermissionDeniedError`, ...) rather than returning an HTTP
status itself — that would violate the service layer's "must not know about HTTP status
codes" rule above. Global exception handlers, registered once in `create_app()`, turn
every `AppError`, validation failure, `HTTPException` and unhandled exception into the
same RFC 7807 problem+json shape, carrying a stable `code` the client can branch on
(BRD A2, B6). No router builds its own error response. Every code is a member of
`ProblemCode`; a refusal the user reads gets its own (`household_currency_mismatch`, not
`domain_error`), and the values it was worded with travel as `params`, so the client can
say it in the user's language (F9.9.5).

## The ingestion pipeline

The most involved flow in the system, and the one where the BRD's constraints bite.

```
upload ──► validate (ReceiptService) ──► store image ──► parse ──► match positions ──► categorise ──► file discounts ──► persist
           (A1, A2)                      (A12, N1)       (A9-A11)    (B1-B9)            (5a)               (C1-C3)       (A12-A15)
```

Three properties of this pipeline are requirements, not implementation choices:

- **Centralized logic via ReceiptService.** Format validation (content inspection, A1/A2), ingestion queuing, and orchestration of the steps below belong to `ReceiptService`, keeping routers thin.
- **S3-compatible Object Storage.** The raw image bytes are physically stored in an S3 bucket encrypted at rest via AES256, returning a persistent identifier (`file_id`) before moving on to parsing (A12, N1). The original artifacts are stored independently of the structured data they produce, but their lifetime is bound to it: deleting a receipt deletes its objects, because a user who erases a receipt has asked for the photo to go too (ADR-0007).
1. **Upload returns before parsing finishes.** The BRD's 10-second target (N4) is a
   processing budget, not an HTTP timeout. Upload persists a job and returns a handle;
   the client polls or subscribes for the result.
2. **Failure is a state, not an exception.** A receipt whose total or date could not be
   read is stored with status `manual_review` and excluded from budget maths (A11, D3).
   It is never dropped and never silently guessed at.
3. **Position matching runs only within one physical receipt.** Deduplication across
   receipts would be a correctness bug: buying milk weekly produces identical line items
   on different receipts, and those are separate purchases (B9).

Categorisation also runs outside the pipeline: `CategorisationService` reassigns a stored
item by hand (`PATCH /receipts/line-items/{id}/category`, C4) and re-runs the categoriser
on one stored receipt (`POST /receipts/{id}/categorise`). The re-run skips every item
marked `is_category_manual`. Both upload and re-run apply the user's correction rules
(`category_rules`, C5) before asking the categoriser, then the same threshold rule
(`app.domain.categories.match_rule` and `confident_category`; ADR-0008). There is
deliberately no bulk re-categorisation of old receipts.

## Persistence

Every domain entity extends `app.models.base.Model` (F0.3.3), which fixes a UUID
primary key (PostgreSQL's `gen_random_uuid()`, built into core since PG13) and
timezone-aware `created_at`/`updated_at` for every table, and a deterministic
constraint-naming convention so autogenerated migrations don't invent a different
name for the same constraint on every run.

A request gets exactly one `AsyncSession`, opened by the `get_db_session` FastAPI
dependency (F0.3.1) and closed at the end of the request: committed if the route
completed without raising, rolled back otherwise. This is the Unit of Work boundary
— a service's whole chain of repository calls shares that one transaction, so a
failure partway through a multi-step mutation cannot leave the database
half-written.

Every schema change ships as an Alembic migration in the same PR as the model
change that produced it (F0.3.2); `alembic revision --autogenerate` drafts one,
but autogenerate is a draft, not a commit — it does not reliably catch renames or
every constraint change, so the generated file is inspected, not trusted. See
[`backend/README.md`](../../backend/README.md#database) for the commands.

## Aggregation and recalculation

Monthly totals derive from receipts, keyed on **transaction date, not upload date**
(D2) — a receipt photographed three weeks late belongs to the month it was bought in.

A completed month is snapshotted (D5), but the snapshot is a cache, not the truth.
Editing, adding or deleting a receipt in a closed month recalculates and rewrites it
(D6, N3). Any code path that mutates a receipt must trigger recalculation; this is the
easiest invariant in the system to break silently.

That is why it is enforced in one place (ADR-0010): a `before_flush` hook drops the
snapshot of every month a pending receipt or line change touches, and the next read
rebuilds it. Only bulk SQL escapes the hook, which is why receipt deletion goes through
the ORM. What F10.3 still owns is the rest of deletion's reach: statistics, once E7
exists.

On the client the same rule has one owner too (F6.5): `ReceiptStore` and `UploadStore`
take an "a receipt changed" callback, which `RootStore` points at
`BudgetStore.refresh()`. Whatever screen a receipt is corrected, deleted or stored
from, including the dashboard's own receipts column, the month view fetches its figure,
its spend by category and its receipts again, and it reopens on the month it was left on.

The landing view gets all three in one round trip (F6.7):
`GET /api/v1/budget/months/{year}/{month}/dashboard`, where `DashboardService` composes
`BudgetService`'s figure (E6) with the receipts repository's spend by category (E5) and
the month's receipts (E3), all bounded by the same month. Which receipts it lists is
the server's call: the newest of a running month, the biggest of a finished one.

Every endpoint that filters by date takes `start` and `end` as plain dates, both
included, parsed once by `app/api/periods.py` into a `DateRange`
(`app/domain/periods.py`, ADR-0012); the repository applies it through one `_within`
filter, and the month view builds its own with `DateRange.of_month`.

Statistics (E7) read the same items over any run of days:
`GET /api/v1/statistics/categories?start=&end=` goes through `StatisticsService`, which
takes the per-category spend from the receipts repository and leaves the ranking and
the shares to `app/domain/statistics.py`, so the rule lives in one pure function. With
`compare=true` the service counts `DateRange.previous()` the same way and
`compare_categories` adds each category's change (F7.3); with `chart=true`,
`app/domain/charts.py` adds the bars, already scaled, for the client to draw (F7.5). Every
one of these period queries filters one user's receipts by
`coalesce(transaction_date, created_at)`; the `ix_receipts_user_purchased` expression
index and `ix_line_items_receipt_id` exist for exactly that (F7.1).

Every one of these sums reads `LineItem.paid`, a `column_property` of the line's total
less its share of a receipt's unprinted discount (F23.7), never `total_price` directly;
the price history is the one reader of the shelf price. `PUT /api/v1/receipts/{id}/discount`
spreads the discount (`app/services/receipt_discount.py`), and a receipt update spreads
it again, so the shares can never disagree with the lines.

Income has its own table and router (F23.10): `GET/POST/PUT/DELETE /api/v1/income`
for a month's entries, the month's figure falling back to the account's usual income
(`app/domain/income.py`), and `GET /api/v1/income/balance?today=` for the balance
(F23.14): the account's starting amount carried forward by income received and spending
counted since, through the same `ReceiptRepository.month_total` the month view uses.
`POST /api/v1/income/read` reads a payslip or transfer confirmation through
`IncomeReaderPort` (`IncomeDocumentAdapter`, the vision model) into a draft that is not
saved; the file stays in memory, and the confirmed entry goes through `POST /income` with
`channel: "document"` (F23.11). A forwarded letter the vision reader calls income
(`ExtractedReceipt.document_kind`) is read again by the same port and kept in
`pending_incomes` instead of becoming a receipt; `GET /income/pending`,
`POST /income/pending/{id}` (confirm) and `DELETE /income/pending/{id}` serve Home's card.

Regular incomes live in `income_sources` (`/api/v1/income/regular`, F23.17) and are
folded into the month by `month_income(recurring=…)` and into the balance by
`regular_since`; taxes for those who pay their own (F23.16) come from the user's rate and
fixed sum, each income's `taxed` flag, and `tax_payments` (`/api/v1/income/taxes`).

Regular bills (F23.18) live in `regular_expenses` (`/api/v1/income/bills`); the month view
returns them with `bills_total`, and the balance takes them off on their day through the
same `Recurring` rule as regular incomes. Spending folds the period's receipts, the items
to file and the bills into sections that open in place (`Collapsible`), and Plan's goals
open in place with a ring each (`goalMeter`).

Explore's months carry what each product cost in them (`MonthPurchases.by_product`), for
columns stacked by product.

Reading a photo stays off the event loop: `prepare_photo` (HEIC to JPEG, upright by EXIF,
at most 3000 px) runs in a thread, the prepared bytes are read from memory rather than
downloaded back, the kept copy is made smaller only after a recheck could have needed
the photo again (`compress_stored`), and litellm is imported at start (`app/main.py`), not inside the first
read — lazily, it froze every request on a new instance for 11-14 s. The browser shrinks
photos to the same 3000 px before sending (`shrinkPhoto`), which keeps a many-shot
receipt under Cloud Run's 32 MB request limit, and a progress poll that fails is retried
rather than reported, since the job runs on regardless.

Spending day by day (`GET /api/v1/statistics/daily`, F23.4) sums the same `paid` per UTC
day and lists every day of the period, a quiet one as zero (`app/domain/daily_spend.py`).
A goal is checked before it is saved by `POST /api/v1/goals/check` (F23.13): the service
reads the last three whole months, `app/domain/goal_check.py` judges — no model call.

## Proactive advice

Advice for goals at risk (BRD F7, F8.8) is prepared by a scheduled pass inside the API
process, started and stopped by `create_app()`'s lifespan (`app/services/proactive_advice.py`,
every `proactive_advice_interval_minutes`, 0 to turn it off). For each user, in their own
session and ownership context, a monthly money goal heading over its cap with no advice
from this month gets some through the same `AdviceService.advise` a request uses. The
warning itself is not stored: `GET /api/v1/goals/progress` works it out from the month's
pace on every look, and only the user's "not now" is kept, on the goal, for the month.
There is no endpoint that triggers the pass; nothing outside the process can.

## Export

Exports (N6, F7.6) run as background jobs, like receipt processing: `POST
/api/v1/exports` records an `ExportJob` with the screen's filters and answers 202 at
once; `app/services/export.py`'s `run_export` then opens its own session and storage
client, reads the owner's data page by page, writes the CSV or JSON to object storage
under `exports/{user_id}/`, and marks the job ready or failed. The client polls
`GET /api/v1/exports/{id}` and downloads `GET /api/v1/exports/{id}/file` once ready. The
statistics JSON is built by the same `statistics_response` the statistics endpoint
returns, so a file and the screen cannot disagree.

## Security posture

- Receipt images and extracted financial fields are encrypted at rest (N1).
- Every user-owned query is filtered by owner in the repository base class, not by each
  call site (N2). Bypassing that filter requires an explicit, greppable escape hatch.
- Cross-user access returns 404, never 403 — a 403 confirms the record exists.
- Automatic classification decisions are logged with confidence scores for audit and
  tuning (N5).
- Spending is bounded in the application, not by the cloud (F10.6): a monthly quota of
  receipt reads per account and a daily ceiling for the whole service, checked before any
  model call (`QuotaService`, injected through `get_quota_service`), plus per-IP limits on
  login, registration, upload, advice and export (`app/api/rate_limit.py`, slowapi,
  counted in memory per instance). Vertex AI offers no per-project cap for Gemini 2.x, and
  the billing budget only alerts.
- An admin account opens the admin console only with a second factor (TOTP, encrypted
  at rest), is mailed on every sign-in, sees no receipts, and leaves a log entry for each
  action; only the super admins named in configuration appoint admins (ADR-0021).
- The agent advises and never moves money. There is no code path to a payment API, by
  design (BRD constraint 11.2).

## Frontend

MobX stores own state and the actions that change it; components observe and render.
Business logic does not live in components — a component that computes a budget total
is a bug, because that number must match what the API computed.

A single `RootStore` is instantiated once and injected into the component tree through
React context; components read it with a `useStores()` hook, never a direct import of
another store (F9.2). See `frontend/src/stores/README.md` for the observable-vs-derived
and async-action conventions every store follows.

The API client is generated from the FastAPI OpenAPI schema in CI, so a backend contract
change breaks the frontend build rather than production (F9.3). `backend/scripts/
export_openapi_schema.py` introspects `create_app()` to produce the schema — no running
server or database needed. `openapi-typescript` turns that into `frontend/src/api/
schema.ts` (generated, checked in, never hand-edited), and `openapi-fetch` provides the
typed runtime client in `frontend/src/api/client.ts`, the only module permitted to reach
the backend. Frontend CI regenerates the schema and fails the build if it differs from
what's committed, so a route or model change with no matching regeneration is caught in
the PR that made it, not after merge.

Colour, radius, spacing and control anatomy come from `docs/design/` — a set of plain
HTML screens plus a token stylesheet that is the design reference for the whole
product, and outranks the code (ADR-0004). A component that hardcodes a hex value
instead of a token is wrong even if the pixels match, because it cannot follow a
retheme. When a built screen and its reference in `docs/design/` disagree, the built
screen is wrong; when implementation shows the reference itself is wrong, fix
`docs/design/` in the same commit as the code that prompted it.

Design v2 (ADR-0022, `docs/design/v2.md`) is the current look: six palettes keyed off
`data-palette` on `<html>` (`ThemeStore`, saved on the account), the tabs Home ·
Spending · ＋ · Products · Plan, and Settings behind the avatar. A new account is
walked through `/welcome` once — `ProtectedRoute` and the signed-in "/" send there while
`users.onboarded_at` is empty — and finishing or skipping it saves the choices with
`onboarded: true` in one `PATCH /users/me`.

The client is also an installable app (PWA, F9.8): `frontend/public/manifest.webmanifest`
and the Apple meta tags in `index.html` make it open full screen from the home screen,
and `public/sw.js` caches only the app itself — content-hashed assets and an offline
page, never API responses, which are financial data and live on another origin.
Pages are fetched network-first, so every deploy reaches installed copies on their next
launch; there is no app store build to keep in step. The worker registers in production
builds only.

Every word the user reads comes from `frontend/src/locales/{en,uk,pl}/<area>.json` through
i18next (F9.9); English is the source the keys are typed against and the fallback, and
`npm run lint:locales` (in CI) fails when Ukrainian or Polish lacks a key, a placeholder
or a plural form. The language is the account's (`users.language`) once signed in, else
the one chosen on this browser, else the browser's own — never the user's location.
`LanguageStore` applies it; dates and amounts go through `numberFormat`/`dateFormat`
(`src/i18n/format.ts`), which format in the current language at the moment they are
called. Receipt contents stay as printed. A server refusal is shown by its `code` from
the `errors` namespace, filled from its `params`, with the English `detail` as the fallback
for a code the client has no words for; a backend test fails when a `ProblemCode` has no
translation. Goal advice is written by the model in the account's language.

The public pages are prerendered (F17.2). `npm run build` also builds
`src/entry-prerender.tsx` for Node and `scripts/prerender.mjs` renders the app's own tree —
`App` under a `StaticRouter`, with the stores on empty stand-ins for the browser's storage,
which is a visitor without a session — into `dist/index.html` (the landing in English, for
"/") and `dist/{en,uk,pl}.html`, each with its language's title, description, Open Graph
tags, canonical address and hreflang links. The browser shows that HTML at once, then
renders its own copy in the reader's language and theme over it; it does not hydrate, so
a reader whose language or session differs from the prerendered page never sees a mismatch.
The untouched build output is kept as `dist/app.html`, and every other route falls back to
it (`firebase.json`), so a signed-in page never shows the landing before the app starts.

## Repository layout and the frontend/backend boundary

```
docker-compose.yml  Local stack (API, client, PostgreSQL, MinIO) — repo root, not infra/,
                     so `docker compose up` works from a fresh clone with no extra flags
backend/             FastAPI service — routers, services, repositories, ports (see Layers above)
frontend/            React + MobX client
infra/terraform/     Production on Google Cloud (ADR-0014, which replaced AWS in ADR-0002)
infra/mail-relay-appengine/  Mail relay on App Engine: receipts in (ADR-0013), letters out (ADR-0019)
infra/dev/           Local-only stand-ins, e.g. the SMTP mail relay
docs/                BRD, architecture, planning, ADRs — this tree
scripts/             Repository tooling (e.g. backlog_sync.py)
```

**No import may cross from `frontend/` to `backend/`, or the reverse, except through
the generated OpenAPI client** (`frontend/`'s API layer, produced from the backend's
OpenAPI schema — see F9.3). Nothing in `backend/` imports from `frontend/` at all; the
dependency is one-directional. This is what keeps the two runtimes deployable and
testable independently, and it is why the client is generated rather than hand-written
— a hand-written client invites exactly the shortcut this rule forbids.

## Configuration and environments

`app.config.Settings` (F0.2.2, F0.7.1) is the only place the service reads
configuration from — every field, its purpose, default and whether it's required is
[`configuration.md`](configuration.md). What differs between the three deployment
tiers (local, staging, production), including which Claude model tier each calls, is
[`environments.md`](environments.md#the-matrix) (F0.7.3). How the two real secrets
(`ANTHROPIC_API_KEY`, the database credential) are stored and rotated per environment
is [`secrets.md`](secrets.md) (F0.7.2).

## Deployment

Production is one environment on Google Cloud (ADR-0014), all of it in
`infra/terraform/`:

```
Firebase Hosting (static frontend) ──HTTPS──► Cloud Run "backend" ──VPC──► Postgres on e2-micro
                                                 │   │                      (daily disk snapshots)
App Engine mail relay ◄─webhook / send + secret──┘   ├──► Cloud Storage (photos, S3 API)
                                                     └──► Vertex AI Gemini (LiteLLM)
```

Every merge to `main` runs `.github/workflows/deploy.yml`, which signs in through Workload
Identity Federation. It builds the backend image, migrates the database with the
`migrate` Cloud Run job, deploys the service, publishes the frontend and the mail relay
when they changed, and checks `/health`. `terraform apply` is a deliberate local step.

## Deliberate non-goals

Out of scope by BRD section 4.2, and worth stating so nobody "helpfully" adds them:
bank integrations, automated payments, tax advice. Budgets, goals and advice are in one
currency per account; only receipts are converted (ADR-0016). Households (E12) read their
members' receipts but never own them, so every write stays owner-only (ADR-0017).
