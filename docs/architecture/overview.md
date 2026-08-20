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
                                    └──►  Claude API     (extraction, categorisation, advice)
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
| **Port** | Protocol describing an external dependency | Reference a concrete vendor SDK |

Services depend on ports, not implementations. `ReceiptParser`, `ItemCategoriser` and
`AdviceGenerator` are protocols; the Claude-backed classes implementing them are wired
in by FastAPI `Depends`. This is what allows the BDD acceptance suite to run the real
business logic against stub implementations with no network access.

### Errors crossing the API boundary

A service or repository that needs to fail the request raises an `app.errors.AppError`
subclass (`NotFoundError`, `PermissionDeniedError`, ...) rather than returning an HTTP
status itself — that would violate the service layer's "must not know about HTTP status
codes" rule above. Global exception handlers, registered once in `create_app()`, turn
every `AppError`, validation failure, `HTTPException` and unhandled exception into the
same RFC 7807 problem+json shape, carrying a stable `code` the client can branch on
(BRD A2, B6). No router builds its own error response.

## The ingestion pipeline

The most involved flow in the system, and the one where the BRD's constraints bite.

```
upload ──► validate ──► store image ──► parse ──► match positions ──► categorise ──► persist
           (A1, A2)     (A12, N1)      (A9-A11)    (B1-B9)            (C1-C3)       (A12-A15)
```

Three properties of this pipeline are requirements, not implementation choices:

1. **Upload returns before parsing finishes.** The BRD's 10-second target (N4) is a
   processing budget, not an HTTP timeout. Upload persists a job and returns a handle;
   the client polls or subscribes for the result.
2. **Failure is a state, not an exception.** A receipt whose total or date could not be
   read is stored with status `manual_review` and excluded from budget maths (A11, D3).
   It is never dropped and never silently guessed at.
3. **Position matching runs only within one physical receipt.** Deduplication across
   receipts would be a correctness bug: buying milk weekly produces identical line items
   on different receipts, and those are separate purchases (B9).

## Aggregation and recalculation

Monthly totals derive from receipts, keyed on **transaction date, not upload date**
(D2) — a receipt photographed three weeks late belongs to the month it was bought in.

A completed month is snapshotted (D5), but the snapshot is a cache, not the truth.
Editing, adding or deleting a receipt in a closed month recalculates and rewrites it
(D6, N3). Any code path that mutates a receipt must trigger recalculation; this is the
easiest invariant in the system to break silently.

## Security posture

- Receipt images and extracted financial fields are encrypted at rest (N1).
- Every user-owned query is filtered by owner in the repository base class, not by each
  call site (N2). Bypassing that filter requires an explicit, greppable escape hatch.
- Cross-user access returns 404, never 403 — a 403 confirms the record exists.
- Automatic classification decisions are logged with confidence scores for audit and
  tuning (N5).
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

## Repository layout and the frontend/backend boundary

```
docker-compose.yml  Local stack (API, client, PostgreSQL, MinIO) — repo root, not infra/,
                     so `docker compose up` works from a fresh clone with no extra flags
backend/             FastAPI service — routers, services, repositories, ports (see Layers above)
frontend/            React + MobX client
infra/terraform/     Cloud deployment IaC — AWS is the target (ADR-0002); Azure was
                     evaluated and deferred, not ruled out
docs/                BRD, architecture, planning, ADRs — this tree
scripts/             Repository tooling (e.g. backlog_sync.py)
```

**No import may cross from `frontend/` to `backend/`, or the reverse, except through
the generated OpenAPI client** (`frontend/`'s API layer, produced from the backend's
OpenAPI schema — see F9.3). Nothing in `backend/` imports from `frontend/` at all; the
dependency is one-directional. This is what keeps the two runtimes deployable and
testable independently, and it is why the client is generated rather than hand-written
— a hand-written client invites exactly the shortcut this rule forbids.

## Deliberate non-goals

Out of scope by BRD section 4.2, and worth stating so nobody "helpfully" adds them:
bank integrations, multi-currency conversion, shared household budgets, automated
payments, tax advice.
