# ADR 0023: Money a household shares

**Date:** 2026-10-19
**Status:** Accepted — F12.8; extends ADR-0017

## Context

ADR-0017 made a household read its members' receipts. Income, regular income and regular
bills (F23.10, F23.17, F23.18) stayed strictly their author's, so a couple's flat, the salary
only one of them earns and the family budget were invisible to the other partner: the
family's money was not the family's. The product's direction is a family budget built from
receipts, for families where one partner may also run a small business, so this gap sits in
its centre.

## Decision

- **Shared or mine.** Each income, regular income and regular bill carries an optional
  `household_id`. Set, it is shared with that household; empty, it is its author's own.
  `user_id` stays the author.
- **Every member reads and changes what is shared.** The three repositories widen their
  ownership filter from "the caller wrote it" to "the caller wrote it, or it is shared with
  the household the caller belongs to" (`SharedWithHousehold`). A child only reads them
  (F12.10, domain model 11m).
- **Each member's own view counts their own and the shared in full.** Shared money is every
  member's money. A shared bill is never divided into parts per member: the budget is
  shared, so the bill comes out of it once, whole. (A first version divided it equally or
  by income; dropped the same week, once a child in the household made a "part" absurd.)
  The household view (F12.9) counts the shared ones once.
- **Leaving takes one's sharing back.** A member who leaves or is removed gets back, as their
  own, what they shared; what the others shared stays with the household. Deleting the
  household returns everything to its authors (`ON DELETE SET NULL`).
- **The household budget is changed by any member,** no longer by the owner only. The owner may keep
  it to themselves, a household setting (F12.10).

## Consequences

- N2's access tests gain the shared case: a member reads and writes a shared row, a stranger
  and a departed member do not (`tests/api/test_shared_money.py`,
  `tests/security/test_cross_household_access.py`).
- `regular_expenses.split`, written by the first version, stopped being read in F12.10 and
  is dropped by the next migration (F23.15), as ADR-0014 asks: code first, column after.
- Accounts (F23.15) will carry the same `household_id`, so a joint account is shared the same
  way.
