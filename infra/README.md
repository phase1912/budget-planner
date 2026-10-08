# infra

Deployment infrastructure. The local development stack is not here — `docker-compose.yml`
lives at the repository root so `docker compose up` works from a fresh clone; see
[the architecture overview](../docs/architecture/overview.md#repository-layout-and-the-frontendbackend-boundary).

| Directory | Contents |
|---|---|
| [`dev/mail-relay/`](dev/mail-relay/) | Local stand-in for the inbound mail receiver: SMTP on `localhost:2525`, started by `docker compose up` (F11.2, [ADR-0013](../docs/adr/0013-inbound-email-through-app-engine.md)) |
| [`terraform/`](terraform/) | Cloud deployment IaC, targeting AWS ([ADR-0002](../docs/adr/0002-cloud-provider-aws.md)) |

Not yet populated — tracked by [F0.4](../docs/planning/backlog.yaml) (local development
environment), [F0.7](../docs/planning/backlog.yaml) (configuration, secrets and
environments), and [F0.9](../docs/planning/backlog.yaml) (cloud deployment infrastructure).
