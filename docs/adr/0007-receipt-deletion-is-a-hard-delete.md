# ADR 0007: Receipt deletion is a hard delete

**Date:** 2026-09-17
**Status:** Accepted

## Context

Until now nothing in the product could delete anything. There was no `DELETE` endpoint
in the API, no write action in the receipts store, and no code path anywhere that removed
an object from storage. A receipt captured by mistake — a duplicate, a misread photo, a
stranger's receipt picked up off a counter — stayed forever.

Adding deletion forces a choice the rest of the system will be built on top of. A receipt
owns three things: a row in `receipts`, its `line_items`, and one or more photographs in
object storage. "Delete" can mean anything from hiding the row to erasing all three.

The BRD does not settle it. N3 speaks about deletion only in terms of budget and
statistics recalculation, and N1/A12 require the photographs to be encrypted at rest
without saying how long they live.

## Decision

Deleting a receipt erases it: the row, its line items and every stored photo, immediately
and irreversibly. There is no `deleted` status, no tombstone row and no recovery window.

The order is deliberate. The row is deleted first and the objects second, inside the
request's transaction, so a storage failure cannot leave a receipt whose photos are
already gone. A failure to delete one photo is logged rather than raised: unreferenced
bytes cost nothing, while rolling back would strand a receipt that is half erased.

The storage port's `delete_file` is idempotent by contract. S3 answers 204 for a key that
was never there, so promising anything else would force a `HEAD` before every `DELETE`
and still lose the race — and would make a half-finished deletion impossible to retry.

## Consequences

**Positive:**
- A user who asks for a receipt to be gone gets that, including the photograph. Soft
  deletion would leave their financial data live in the database and their image live in
  the bucket after they asked for erasure, which contradicts the security posture in
  `docs/architecture/overview.md`.
- No aggregation, statistic or snapshot has to learn about a "deleted but present" state.
  E6, E7 and F10.3 can sum what they find.
- Storage does not accumulate objects nothing references.

**Negative:**
- **There is no undo.** A mis-click destroys the photograph. The confirm dialog is the
  only guard, which is why it names the merchant, the total, the item count and the photo
  count rather than asking "are you sure?".
- **Statistics can never reconstruct a deleted receipt.** Any future report of "what
  changed this month" has nothing to point at.
- **There is no deletion audit trail.** F10.4 logs classification decisions; if deletions
  ever need auditing too, that is a new record written before the erase, not something
  recoverable from the data.
- The lifetime of an S3 object is now coupled to a database row. A restore of the
  database without a matching restore of the bucket produces receipts with dead photos.

## Alternatives considered

**Soft delete (a `deleted_at` column).** Recoverable and audit-friendly, and it would slot
neatly under F10.4 and F11's account export. Rejected because it does not do what the user
asked: the data and the photograph both survive. It also taxes every future query with a
filter that is easy to forget — precisely the failure mode invariant 22 exists to prevent.

**Hard delete of the row, deferred sweep of the photos.** Avoids the window where the
database and the bucket disagree. Rejected as premature: it needs a job runner the project
does not have, to solve a failure whose only symptom is wasted bytes.
