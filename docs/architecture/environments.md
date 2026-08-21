# Environments

Three deployment tiers exist: **local**, **staging**, **production**
(`app.config.Environment`, F0.7.3). This document is what differs between them and why
— which config values each sets is [`configuration.md`](configuration.md)'s table;
where secrets specifically come from is [`secrets.md`](secrets.md).

What is deliberately **not** here: compute target, state backend, and the concrete AWS
topology for staging/production. Those are real infrastructure design decisions, made
when F0.9 (cloud deployment infrastructure) is groomed and picked up — see its entry in
`docs/planning/backlog.yaml` — not guessed at here. This document fixes the *behavioural*
matrix (what a service in each tier does differently); F0.9 fixes *how* staging and
production actually run.

## The matrix

| | Local | Staging | Production |
|---|---|---|---|
| **Purpose** | Day-to-day development | Catch integration/deployment defects before they reach users | Serve real users |
| **`ENVIRONMENT`** | `local` (default) | `staging` | `production` |
| **Runs on** | `docker-compose.yml` on the developer's machine | AWS (ADR-0002), provisioned by F0.9 | AWS (ADR-0002), provisioned by F0.9 |
| **Config source** | `backend/.env` (gitignored, copied from `backend/.env.example`) | Environment variables injected at deploy time by F0.9's infrastructure-as-code | Environment variables injected at deploy time by F0.9's infrastructure-as-code |
| **Secrets source** | Local `.env` file, placeholder-only in git (`.env.example`) | GitHub Actions repository secrets at deploy time, then a managed secrets store on AWS at runtime — see [`secrets.md`](secrets.md) | Same category as staging, with production's own credentials — never shared with staging |
| **Database** | Postgres container, named volume, disposable (`make down -v` wipes it) | A real, network-reachable Postgres, seeded with synthetic data | A real, network-reachable Postgres |
| **Authoritative for user data?** | No — throwaway, recreated at will | **No** — staging data is test data; it is never migrated into production, and production data is never copied into staging (BRD constraint 11.1, N1: real financial data does not belong in a lower-trust tier) | **Yes** — the only tier whose data represents real users and real money |
| **Object storage** | MinIO container (S3-compatible stand-in, ADR-0002) | S3 | S3 |
| **`ANTHROPIC_MODEL`** | `claude-haiku-4-5-20251001` (default) — fast, cheap, sufficient for developing against synthetic receipts | `claude-haiku-4-5-20251001` (default) — staging validates deployment and integration, not extraction accuracy | `claude-sonnet-5` (set explicitly) — real users' figures depend on extraction accuracy; see ADR-0005 for the cost/accuracy trade-off |
| **Confidence thresholds** | Same defaults as every tier (`0.80` OCR / `0.70` categorisation, ADR-0005) — these are business-rule constants, not environment-tuned | Same | Same |
| **CI** | `.github/workflows/backend-ci.yml` / `frontend-ci.yml` run against a throwaway Postgres service container with a placeholder `ANTHROPIC_API_KEY` — no real credential, and the Anthropic API is never actually called (AI calls are stubbed at the port for tests) | — | — |

## Why CI is not its own row in the matrix

CI is not a fourth tier. `backend-ci.yml`/`frontend-ci.yml` exercise the same
`ENVIRONMENT=local` code path as a developer's machine — the point of CI is to prove
the code works, not to be a deployment target. It gets its own line in the table above
only because its `ANTHROPIC_API_KEY` handling is worth calling out explicitly.

## Adding a new per-environment setting

A new tunable belongs on `app.config.Settings` (F0.7.1) with a sensible local default,
documented in [`configuration.md`](configuration.md). Whether staging/production need a
different value is then a deploy-time env var, set where F0.9's infrastructure-as-code
sets `ANTHROPIC_MODEL` today — never a branch on `environment` inside application code
(see ADR-0005's reasoning for `anthropic_model`).
