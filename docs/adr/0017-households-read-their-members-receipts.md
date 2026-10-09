# ADR 0017: A household reads its members' receipts; it never owns them

**Date:** 2026-10-09
**Status:** Accepted — F12.1.1; answers the BRD's open question 3 (section 14) and moves
shared budgets out of the section 4.2 non-goals

## Context

E12 lets a couple or a family keep one budget. Everything built so far assumes one owner per
receipt: every repository filters by `user_id` (the ownership filter in `BaseRepository`,
F1.3), N2's cross-user tests check exactly that, and the month, statistics, goals and advice
are computed per user.
Two models were open:

1. **The user owns the receipt and the household reads it.** `user_id` stays; membership adds
   read access.
2. **The household owns the receipt.** Every receipt, budget and statistic moves to a
   household id, and a single user becomes a household of one.

The second rewrites every repository and every access test for a gain the product does not
need: nobody but the person who added a receipt has a reason to change it.

## Decision

- **A receipt stays its owner's.** `user_id` is unchanged and every write — edit, delete,
  recategorise, keep-duplicate — still goes through the owner-only filter. Membership adds
  read access and nothing else.
- **One household per user**, with two roles: the **owner**, who created it and may rename
  it, set its budget, regenerate its invite link and remove members, and **members**, who
  may leave. The owner cannot leave while others remain; the last one out deletes it.
- **Joining is by an invite link** the owner shares however they like (F12.3); no mail
  provider is involved. Regenerating the link stops the old one working.
- **Joining shares everything, except receipts marked private.** A member chooses what to
  hide rather than what to show, so the household budget is complete without anyone having
  to remember to share.
- **A private receipt hides its details, never its money.** It counts in the household's
  totals and budget, but the household sees one line per member per month — "Private —
  Anna: 120 PLN" — with no merchant, items, category or date: a date and an amount are
  already enough to guess. To its owner it is an ordinary receipt.
- **One currency per household.** Its totals are in the members' account currency, so
  joining with a different one is refused with the reason (ADR-0016).
- **Goals and advice stay personal.** The household gets BR-4's month and BR-5's
  statistics; goals and advice keep reading only the user's own receipts.

## Consequences

- N2 still holds for writes word for word. For reads it becomes "a user reads their own
  receipts and their household's shared ones"; F12.6 tests that every household-aware
  endpoint keeps to it, and that leaving or removal revokes access at once.
- The personal views — month, statistics, goals, advice — are unchanged; the household ones
  are added beside them behind a "Mine / Household" switch.
- With exactly one private receipt in a month, the household learns its amount. That is the
  price of a budget that adds up, and it is said where a receipt is marked private.
- A user with receipts in a household's history who leaves takes them along: their
  receipts were always theirs, so the household's past months shrink. Snapshots of finished
  household months are not kept for that reason.
