# ADR 0010: Monthly snapshots are taken on first look and dropped on change

**Date:** 2026-09-26
**Status:** Accepted

## Context

BRD D5 asks for a finalised snapshot to be generated and persisted when a month is
complete. D6 and N3 ask for it to be recalculated when a receipt in that month is added,
edited or removed. The backlog adds that F6.4 must say how the transition is triggered
across user time zones.

The project has no job scheduler. ADR-0009 made the user's browser the only source of
"today": which month is over depends on the user's clock, and no timezone is stored.
The architecture overview already calls a snapshot "a cache, not the truth" and warns
that recalculating on every receipt change is the easiest invariant here to break
silently.

## Decision

**Taken on first look.** The first time a user requests a month that is over by their
clock, the service computes it from the receipts and stores it (`monthly_snapshots`,
one row per user and month). From then on the month is read from that row. No scheduler
is needed, and the time-zone question answers itself: the transition happens on the
user's own calendar.

**Guarded against a clock running ahead.** A month is stored only once it has ended
somewhere on Earth, meaning its end has passed in UTC+14 (`may_finalise`). A browser
whose clock says "December" gets the finalised label but stores nothing, so it cannot
freeze a month that is still running.

**Dropped on change, in the flush.** A SQLAlchemy `before_flush` hook
(`app.db.snapshot_invalidation`) deletes the snapshot of every month a pending receipt or
line-item change touches, in the same transaction. For a receipt moved between months,
that covers both the old month and the new one. The next look rebuilds the snapshot.
Hooking the flush, rather than each code path, covers paths not yet written.

## Consequences

- Bulk `UPDATE` and `DELETE` statements bypass the ORM, and so the hook. Receipt deletion
  was a bulk statement, so `ReceiptRepository.delete` now deletes through the ORM. Any new
  bulk statement that changes receipt dates, statuses or line totals must invalidate for
  itself. Category moves do not, since totals do not depend on categories.
- A month nobody opens after it ends is never snapshotted. Nothing reads a snapshot
  except that same look, so nothing is lost. A future job, for example a monthly report,
  can call the same service.
- The hook runs on every flush. It only issues a statement when receipts or lines are
  pending, so ordinary flushes pay nothing.
