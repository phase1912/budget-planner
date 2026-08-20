# AI Budget Agent

An agent that turns a photo of a paper receipt into structured, categorised spending data,
and uses that data to give goal-driven budget advice grounded in what the user actually
bought — not just where they shopped.

The problem it addresses: bank and card feeds show that 84.50 PLN went to a supermarket, but
not whether that was groceries, alcohol or cleaning supplies. Receipts contain that detail.
Typing it in by hand is why people abandon budgeting apps. So the only action asked of the
user is taking a photo.

## Status

Early foundation work (epic E0). `backend/` has the FastAPI skeleton, config, error
handling and the PostgreSQL/SQLAlchemy/Alembic baseline; `frontend/` has the React/Vite
scaffold and generated API client. `docker-compose.yml` brings up local PostgreSQL and
MinIO — see [backend/README.md](backend/README.md#database). A full clone-to-running
quickstart is F0.4.4, not written yet.

## Stack

Python 3.12 · FastAPI · PostgreSQL · SQLAlchemy 2 · Alembic · React · TypeScript · MobX ·
Vite · Claude API for extraction, categorisation and advice. Rationale in
[ADR-0001](docs/adr/0001-technology-stack.md).

## Documentation

| Document | What it is |
|---|---|
| [Business Requirements](docs/requirements/ai-budget-agent-brd-v1.1.md) | What the product must do. EARS requirements with Gherkin acceptance scenarios. |
| [Backlog](docs/planning/backlog.md) | 11 epics broken into features and tasks, traced back to BRD requirement IDs. |
| [`backlog.yaml`](docs/planning/backlog.yaml) | The machine-readable source of that backlog. |
| [Working agreement](docs/planning/working-agreement.md) | How the plan turns into commits, and how it is changed when reality disagrees with it. |
| [Decisions](docs/adr/) | Architectural decision records. |

## Delivery shape

| Epic | Scope | BRD |
|---|---|---|
| E0 | Foundation & delivery platform | — |
| E1 | Identity & account | N2 |
| E2 | Receipt ingestion & storage | BR-1 |
| E3 | Receipt parsing & extraction | BR-1 |
| E4 | Multi-photo position matching | BR-2 |
| E5 | Spend categorization | BR-3 |
| E6 | Monthly budget calculation | BR-4 |
| E7 | Statistics, comparison & export | BR-5 |
| E8 | Goals & AI optimization advice | BR-6 |
| E9 | Web client foundation | — |
| E10 | Security, privacy & observability | N1–N5 |

E0 and E1 are decomposed into tasks. The rest carry features and are broken down as they are
picked up — see the [working agreement](docs/planning/working-agreement.md) for why.
