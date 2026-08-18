# ADR-0002 — Target cloud provider: AWS

- **Status:** Accepted
- **Date:** 2026-08-18

## Context

The BRD says nothing about deployment; ADR-0001 fixed the application stack but not
where it runs. `infra/` needs a home for infrastructure-as-code before Terraform is
written, and that choice determines which provider's resources the code targets.

## Decision

AWS is the target cloud for deployment. Infrastructure-as-code lives in
`infra/terraform/`, written with AWS resources and variables.

Azure was named as an alternative but not evaluated in depth; this decision does not
rule it out for a later environment, only fixes AWS as the one built first.

## Consequences

- `infra/terraform/` is written against AWS providers/resources. A second provider
  later means either a parallel module tree or an abstraction layer, neither of which
  is justified before a second target actually exists.
- Which AWS services back the application (compute, database, object storage, secrets)
  is not decided by this ADR — that is real design work, done when the deployment
  feature is picked up, not guessed at while establishing repository layout.
