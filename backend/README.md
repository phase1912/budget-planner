# backend

The FastAPI service. Owns all business logic and is the only thing that talks to
PostgreSQL, object storage or the Claude API.

Nothing here imports from `frontend/`. See [the architecture overview](../docs/architecture/overview.md#repository-layout-and-the-frontendbackend-boundary)
for the layering (router → service → repository → port) and the import boundary rule.

## Getting started

Dependencies are managed with [uv](https://docs.astral.sh/uv/). From this directory:

```
uv sync          # create .venv and install runtime + dev dependencies
uv run pytest    # run the test suite
```

`pyproject.toml` pins Python 3.12 and the runtime dependencies fixed by
[ADR-0001](../docs/adr/0001-technology-stack.md) (FastAPI, SQLAlchemy 2.x, Alembic,
pydantic-settings, anthropic) in `[project.dependencies]`; dev-only tooling lives in
the `dev` group under `[dependency-groups]`. `uv.lock` is committed so every install
resolves to the same versions.

No application code yet — that is [F0.2](../docs/planning/backlog.yaml) (application
skeleton) and [F0.3](../docs/planning/backlog.yaml) (PostgreSQL/SQLAlchemy/Alembic).
