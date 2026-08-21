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
scaffold and generated API client. `docker-compose.yml` brings up the full local
stack — API, client, PostgreSQL and MinIO — see [backend/README.md](backend/README.md#database).

## Quickstart

Prerequisites, with the versions this project is built against:

- [Docker Engine](https://docs.docker.com/engine/install/) 24+ with the Compose v2
  plugin (the `docker compose` subcommand — not the standalone `docker-compose`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — manages the Python
  3.12 the backend needs itself; no separate Python install required
- `make` — ships with macOS and most Linux distributions; runs the task-runner targets
  below (F0.4.2)
- A Claude API key from the [Anthropic Console](https://console.anthropic.com/settings/keys)
  — the backend fails to start without one (`app.config.Settings`)

Clone and configure:

```
git clone https://github.com/phase1912/budget-planner.git
cd budget-planner
cp .env.example .env                    # postgres/MinIO credentials, ANTHROPIC_API_KEY
cp backend/.env.example backend/.env    # DATABASE_URL for host-run alembic/uv commands
```

Set `ANTHROPIC_API_KEY` in both `.env` files to your key from the Anthropic Console
above; the defaults for everything else already match between the two files. See
[Configuration](docs/architecture/configuration.md) for every other setting, its
default, and whether it's required.

Bring up the stack and apply migrations:

```
make up          # postgres, MinIO, the API (:8000) and the client (:5173)
make migrate      # in a second terminal, once postgres is healthy
```

The client is now at [localhost:5173](http://localhost:5173), the API at
[localhost:8000/docs](http://localhost:8000/docs). `make down` stops everything;
database and object-store contents persist in named volumes across restarts.

Day-to-day workflow: `make test`, `make lint`, `make typecheck` run both languages'
checks with one command each. See [backend/README.md](backend/README.md) and
[frontend/README.md](frontend/README.md) for running either side on the host instead
of in a container, and [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full ticket-first
process.

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
| [Design reference](docs/design/README.md) | What every screen should look like. Open `docs/design/index.html` in a browser and click through. |
| [Working agreement](docs/planning/working-agreement.md) | How the plan turns into commits, and how it is changed when reality disagrees with it. |
| [Decisions](docs/adr/) | Architectural decision records. |
| [Configuration](docs/architecture/configuration.md) | Every setting the backend reads: env var, default, required or not. |
| [Environments](docs/architecture/environments.md) | What differs between local, staging and production. |
| [Secrets](docs/architecture/secrets.md) | What secrets exist, where they're stored, and how they're rotated. |

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
