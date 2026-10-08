# infra

Deployment infrastructure. The local development stack is not here — `docker-compose.yml`
lives at the repository root so `docker compose up` works from a fresh clone; see
[the architecture overview](../docs/architecture/overview.md#repository-layout-and-the-frontendbackend-boundary).

| Directory | Contents |
|---|---|
| [`dev/mail-relay/`](dev/mail-relay/) | Local stand-in for the inbound mail receiver: SMTP on `localhost:2525`, started by `docker compose up` (F11.2, [ADR-0013](../docs/adr/0013-inbound-email-through-app-engine.md)) |
| [`terraform/`](terraform/) | Production on Google Cloud ([ADR-0014](../docs/adr/0014-google-cloud-deployment.md)): how to bootstrap, apply, restore and stop costs is in its README |
| [`mail-relay-appengine/`](mail-relay-appengine/) | Inbound mail relay deployed to App Engine by the Deploy workflow ([ADR-0013](../docs/adr/0013-inbound-email-through-app-engine.md)) |
