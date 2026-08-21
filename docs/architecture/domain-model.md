# Domain model and business rules

The entities, what they mean, and the rules that must hold. This is the global business
logic reference — when a rule here and the code disagree, one of them is a bug.

**Keep this document current.** A change to a business rule updates this file in the same
commit. Add the BRD requirement ID so the rule stays traceable to its source.

## Entities

| Entity | Meaning | Owned by |
|---|---|---|
| **User** | An account. Holds currency, optional monthly budget limit, and a role (`user` or `admin`) — N2's per-user isolation applies to an admin exactly as to any other account (G8). | — |
| **IdentityLink** | A linked Google or Facebook identity, verified-email-gated (G9-G11). | User |
| **Receipt** | One purchase transaction, from one or more photos. | User |
| **LineItem** | One position on a receipt: product, quantity, unit price, total. | Receipt |
| **Category** | A spending classification. Either a system default or user-defined. | User (nullable for defaults) |
| **PositionMatch** | A decision that two line items are, or are not, the same physical purchase. | Receipt |
| **MonthlySnapshot** | A finalised monthly total. A cache of derived data. | User |
| **Goal** | A financial or lifestyle objective the user declared. | User |
| **Recommendation** | Generated advice tied to a goal, with projected impact and user feedback. | User |

Relationships: a User has many Receipts; a Receipt has many LineItems; a LineItem has one
Category; a Goal produces many Recommendations; a User has many IdentityLinks.

**Not yet groomed:** BR-7 (G1-G12, added by F0.10.1) is fully specified in the BRD, but
E1 as currently groomed (`docs/planning/backlog.yaml`) implements only G1-G7 —
registration, login, session refresh. G8 (admin role) and G9-G12 (OIDC linking) need
their own tasks before BR-7 is delivered; `IdentityLink` and `User.role` above describe
the target, not something built yet.

## Receipt lifecycle

```
uploaded ──► parsing ──┬─► parsed          (counts toward budget)
                       ├─► manual_review   (excluded until resolved)
                       └─► failed          (parsing impossible)
```

`manual_review` is not an error state — it is a receipt that exists and is known to be
incomplete. It stays visible to the user and stays out of the arithmetic (A11, D3).

## Invariants

Rules that must hold at all times. Each is a candidate for a test.

**Money and dates**

1. Monetary values are `Decimal`. Never `float` — binary floating point cannot represent
   currency exactly, and these numbers are shown to users as their own money.
2. A receipt belongs to the month of its **transaction date**, never its upload date (D2).
3. Timestamps are timezone-aware UTC. Month boundaries are derived, and a naive datetime
   silently shifts a receipt into the wrong month near midnight.

**Aggregation**

4. A monthly total is the sum of line-item totals of `parsed` receipts in that month (D1).
5. Receipts in `manual_review` are excluded, and their count and value are reported
   alongside the total — the number is never quietly incomplete (D3).
6. An in-progress month is always labelled incomplete wherever it is displayed (D4).
7. Snapshots are derived data. Any mutation of a receipt in a snapshotted month
   recalculates it (D6, N3).

**Position matching**

8. Two positions match only if name, unit price, quantity and total price are all
   exactly equal (B2, B3). Any difference means different position (B4).
9. Matching is only ever performed between photos of one physical receipt (B5).
10. Identical items on two distinct receipts are two purchases, never duplicates — this
    is normal repeat buying (B9).
11. A user override wins over any automatic determination and is stored as labelled data
    for future tuning (B7, B8).

**Categorisation**

12. Every line item has a category. Below the confidence threshold it is `Uncategorized`
    and flagged for review, never guessed (C2, C3).
13. A manual category override is never overwritten by a later automatic pass (C4).
14. A correction creates a rule for future items with the same or similar name from the
    same merchant (C5).

**Advice**

15. Recommendations cite the user's actual purchase history. Generic financial tips are a
    defect, not a fallback (F3, constraint 11.3).
16. Every recommendation quantifies its projected impact, computed from real history
    rather than asserted by the model (F4).
17. Below the minimum history threshold, the system says more data is needed and produces
    no recommendation (F5).
18. When spend is on track, report progress and suggest nothing (F6).

**Identity**

19. Login and registration return an identical generic error whether the email is
    unknown or the password is wrong (G2, G4).
20. Refresh tokens rotate on use; presenting one already exchanged revokes every token
    issued from that session (G5, G6).
21. An OIDC identity links to an existing account only when the provider reports a
    verified email matching it; an unverified email never links automatically (G10, G11).

**Access**

22. Every query for a user-owned entity is filtered by owner (N2).
23. A request for another user's record returns 404, not 403 (N2).

## Open decisions

These are unanswered in the BRD (section 14) and block the epics named. Record the answer
here as an ADR when it arrives.

| Question | Blocks |
|---|---|
| Confidence thresholds for OCR, categorisation and manual-review triggers | E3, E5 |
| Whether budget periods are strictly calendar months or support custom cycles | E6 |
| Whether thin history yields softened advice or none at all | E8 |
| Target values for the success metrics (section 12) | Not epic-blocking — informs tuning throughout |
| Which markets/currencies ship at launch, and whether multi-currency is truly out of scope | F1.4 |
| Whether household/shared budgets change the single-user assumption | Resolved — phase 2, see E12 in `docs/planning/backlog.yaml` |
