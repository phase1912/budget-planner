# Contributing

This project is worked ticket-first: every behavioural change is attached to a GitHub
issue, implemented on its own branch, and lands through a pull request. A one-line typo
fix does not need this; anything that changes behaviour does.

## Finding or writing the ticket

The plan lives in [`docs/planning/backlog.yaml`](docs/planning/backlog.yaml) — GitHub
issues are a generated projection of it, kept in sync by `scripts/backlog_sync.py`.
Editing an issue body on GitHub is pointless; the next sync overwrites it.

- If a ticket already exists for the change, its acceptance criteria are the definition
  of done — implement against those, not your own read of the goal.
- If it does not exist, add it under the relevant feature in `backlog.yaml` with a
  `title` and a `detail` stating the requirements and acceptance criteria, tracing it to
  a BRD requirement ID where one applies. Then run:

  ```
  scripts/backlog_sync.py render
  scripts/backlog_sync.py sync
  ```

  and commit the YAML and the regenerated `docs/planning/backlog.md` before starting
  the work itself.

See [`docs/planning/working-agreement.md`](docs/planning/working-agreement.md) for the
full cycle, including how the project board moves.

## Branch naming

Always branch from an up-to-date `main`:

```
git switch main && git pull
git switch -c task/<backlog-key-with-dashes>-<short-slug>
```

For example, task F1.2.3 ("Refresh token rotation") becomes:

```
task/F1-2-3-refresh-token-rotation
```

## Commit messages

Imperative subject line, under ~70 characters, followed by a body explaining **why**
the change was needed — assume the reader has the diff and lacks the surrounding
context. Do not add `Co-Authored-By` trailers.

## Pull requests

The PR body must:

- Contain a literal closing keyword and the issue number, e.g. `Closes #42`. A bare
  mention of the number will not resolve the issue or move the board card — GitHub's
  `closingIssuesReferences` needs the keyword.
- Name the BRD requirement IDs the change satisfies, where applicable.
- Explain anything a reviewer would otherwise have to reconstruct: why this approach,
  what was deliberately left out.

Before opening the PR, make sure lint, type checks and the full test suite pass —
`make lint`, `make typecheck` and `make test` run both languages' checks with one
command each. CI runs the same checks and will not merge a red build.

## Code conventions

- **Python**: type hints everywhere, `mypy --strict`, formatted and linted with `ruff`
  (config in `backend/pyproject.toml`). Money is `Decimal`, never `float`. Timestamps
  are timezone-aware UTC.
- **TypeScript / React**: `strict: true`, no `any`. MobX stores own state and actions;
  components observe and render. The API client is generated from the OpenAPI schema —
  never hand-written.
- Both languages: routers/components stay thin — business rules live in services and
  stores, not in HTTP handlers or JSX.

See [`docs/architecture/overview.md`](docs/architecture/overview.md) for how the system
is built and [`docs/architecture/domain-model.md`](docs/architecture/domain-model.md)
for the business rules and invariants those conventions protect. A change to either
should update the corresponding document in the same commit.

## Tests

Nothing is done without tests:

- BRD acceptance scenarios are covered with `pytest-bdd`, wording preserved verbatim
  from [the BRD](docs/requirements/ai-budget-agent-brd-v1.1.md).
- Business rules get unit tests that run without a database.
- Every user-owned resource gets a cross-user access test.
- AI calls are stubbed at the port — a test that hits the network is not a test.
