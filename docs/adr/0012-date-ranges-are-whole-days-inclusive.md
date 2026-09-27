# ADR 0012: A date range is whole days, both ends included

**Date:** 2026-09-27
**Status:** Accepted

## Context

BRD E2 asks for statistics over arbitrary date ranges, and the backlog asks for their
boundary semantics to be defined once and applied everywhere. Until F7.2 the rule was
written out nine times: the backend compared against `end <= 23:59:59` in two
repository filters, subtracted a second from the month's end on the dashboard and kept
a `last_instant` in the statistics; the frontend appended `T00:00:00Z` and `T23:59:59Z`
in five places. The receipts and categorisation lists took timestamps, statistics took
dates. A purchase stamped 23:59:59.5 fell outside its own day.

## Decision

A date range is a run of **whole days, both ends included**, and exists once:

- `DateRange` (`backend/app/domain/periods.py`) holds a first and a last day. Its
  bounds are midnight starting the first day and midnight after the last, the upper one
  exclusive. A range that ends before it starts is a `ValueError`.
- The API names a range as `start` and `end`, plain `YYYY-MM-DD` dates, on every
  endpoint that filters by date. `app/api/periods.py` turns them into a `DateRange` and
  answers 422 `invalid_period` for a backwards range or for one end without the other.
- The repository filters through one `_within(period)` on the date a receipt is filed
  under (its printed date, else its upload date). The month view uses
  `DateRange.of_month`, so a month total and its statistics cannot disagree.
- The frontend sends plain dates and never builds a time of day.

## Consequences

- `/receipts` and `/receipts/line-items` now take `start`/`end` dates instead of
  `start_date`/`end_date` timestamps; the generated client and every caller changed
  with them.
- A future filter reuses `DateRange` and `optional_period`/`required_period` rather than
  writing its own bounds.
- Days are read on the receipt's printed wall clock (ADR-0009): a range is the user's
  calendar days, with no timezone conversion.
