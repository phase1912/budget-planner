# ADR-0001 — Technology Stack

- **Status:** Accepted
- **Date:** 2026-08-18

## Context

The BRD (`docs/requirements/ai-budget-agent-brd-v1.1.md`) specifies business behaviour
only and is deliberately silent on technology. A stack decision is required before the
backlog can be decomposed into implementable tasks, because task granularity depends on
the runtime, ORM, migration tool and state-management model in use.

## Decision

| Layer | Choice |
|---|---|
| Backend | Python 3.12 + FastAPI (async) |
| Persistence | PostgreSQL + SQLAlchemy 2.x (async) + Alembic |
| Frontend | React + TypeScript + Vite |
| Frontend state | MobX |
| AI / extraction | Claude API (vision for receipt OCR, text for categorisation and advice) |
| Object storage | S3-compatible (MinIO locally) for receipt images |
| Tests | pytest, pytest-asyncio, pytest-bdd (Gherkin from the BRD), Vitest |

## Consequences

- Two runtimes and two dependency toolchains must be maintained (`uv` for Python,
  `npm` for the client), and CI needs a job per side.
- The BRD's Gherkin acceptance scenarios can be executed directly via `pytest-bdd`,
  so the acceptance criteria become the regression suite rather than prose.
- The OpenAPI schema FastAPI emits is the contract for the generated TypeScript client,
  which keeps front and back in sync without a hand-written API layer.
- MobX implies class-based observable stores; store boundaries are defined once in
  epic E9 so that feature epics do not each invent their own conventions.
