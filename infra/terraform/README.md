# infra/terraform

Infrastructure-as-code for deploying the application to AWS (see
[ADR-0002](../../docs/adr/0002-cloud-provider-aws.md)).

Not yet written. Deliberately empty: writing Terraform now, before compute, database
and secrets choices are made, would mean guessing at architecture rather than
designing it. Tracked by **F0.9** in [the backlog](../../docs/planning/backlog.yaml) —
grooming that feature (deciding compute target, state backend, environments) is a
prerequisite to writing any `.tf` file here.
