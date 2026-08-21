# Secret handling

Every credential this system uses, where it lives per environment, how it is rotated,
and what catches one that leaks (F0.7.2). No credential is ever committed — see
[Secret scanning](#secret-scanning-on-this-repository) for the backstop if that rule is
broken by accident.

## Inventory

| Secret | Used for | Local | CI | Staging / production |
|---|---|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API calls (`app.config.Settings.anthropic_api_key`) | `backend/.env`, gitignored | `.github/workflows/backend-ci.yml`'s `env:` — a placeholder value (`sk-ant-ci-placeholder`); no test calls the real API (AI calls are stubbed at the port) | A managed secrets store on AWS (ADR-0002), provisioned by F0.9, injected as an environment variable at deploy time |
| Database credentials (embedded in `DATABASE_URL`) | Postgres connection (`app.config.Settings.database_url`) | `backend/.env`, gitignored — matches `docker-compose.yml`'s default `budget_planner`/`budget_planner`, deliberately not a secret worth protecting locally | A throwaway Postgres service container per workflow run, credentials fixed in the workflow file — recreated every run, nothing to rotate | Same managed secrets store as `ANTHROPIC_API_KEY`, a distinct credential per environment (staging's database credential is never valid against production, or vice versa) |
| `PROJECTS_TOKEN` | Board automation (`pr-board-sync.yml`) moving PRs to Review — the default `GITHUB_TOKEN` cannot write to Projects v2 | — | A classic PAT with `repo` + `project` scopes, stored as a GitHub Actions repository secret. Full detail: [`working-agreement.md`](../planning/working-agreement.md#board-automation-secret) — not duplicated here since it is a delivery-tooling secret, not an application one | — |

Nothing else in the codebase reads a credential — `app.config.Settings` is the only
module permitted to (`backend/tests/test_config.py::test_no_direct_os_environ_reads_outside_the_config_module`
enforces this for application secrets; `PROJECTS_TOKEN` is consumed by the workflow
YAML directly, not by application code).

## Rotation procedure

Applies to `ANTHROPIC_API_KEY` and database credentials — the two secrets an actual
deployment depends on. Rotate immediately on suspected compromise (a leaked key, a
departed collaborator, a secret-scanning alert); otherwise, a periodic rotation is not
yet scheduled — this is a solo project (see `.github/CODEOWNERS`) with no deployed
environment yet (F0.9 is not built), so there is no running secret to rotate on a clock
until one exists. Revisit this once F0.9 ships a real staging/production deployment.

1. **Generate the new credential** without invalidating the old one yet — a new key in
   the [Anthropic Console](https://console.anthropic.com/settings/keys), or a new
   database role/password alongside the existing one.
2. **Update the secret store** for every environment that uses it: the GitHub Actions
   repository secret (`gh secret set`, or Settings → Secrets and variables → Actions)
   for CI-facing secrets, and the AWS secrets store (once F0.9 exists) for
   staging/production.
3. **Redeploy or restart** whatever reads the secret at process start — `Settings` is
   only constructed once per process (`get_settings` is `lru_cache`d), so a running
   process keeps the old value until it restarts.
4. **Verify** the new credential works (a successful request in the target
   environment) before the next step.
5. **Revoke the old credential** — delete the old Anthropic key in the Console; drop the
   old database role. Skipping this step is what makes step 1's "without invalidating
   the old one yet" safe to have done, and leaving it undone is what makes a rotation
   incomplete.

## Secret scanning on this repository

GitHub's secret scanning and push protection are both **enabled** on this repository
(Settings → Code security → Secret scanning; verified via `gh api repos/phase1912/
budget-planner` → `security_and_analysis`). Push protection rejects a push that
contains a recognisable credential pattern before it reaches the remote at all — this
is the primary backstop for the "no credential ever committed" rule in `docs/planning/
backlog.yaml`'s F0.7 intent, catching a mistake before `.gitignore` would even need to.

If a scanning alert fires anyway (a secret that reached history before protection was
enabled, or a pattern push protection didn't recognise): treat the credential as
compromised and follow the [rotation procedure](#rotation-procedure) above immediately,
starting from step 1 — do not wait to confirm whether it was actually exposed.
