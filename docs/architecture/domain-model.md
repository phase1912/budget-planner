# Domain model and business rules

The entities, what they mean, and the rules that must hold. This is the global business
logic reference — when a rule here and the code disagree, one of them is a bug.

**Keep this document current.** A change to a business rule updates this file in the same
commit. Add the BRD requirement ID so the rule stays traceable to its source.

## Entities

| Entity | Meaning | Owned by |
|---|---|---|
| **User** | An account. Holds identity (`first_name`, `last_name`, `email`), currency, optional monthly budget limit, and a role (`user` or `admin`) — N2's per-user isolation applies to an admin exactly as to any other account (G8). | — |
| **User Attributes** | | |
| `id` | UUID | Primary key (generated via `gen_random_uuid()`) |
| `email` | String | Unique, used for authentication |
| `first_name` | String | User's first name |
| `last_name` | String | User's last name |
| `password_hash` | String | Argon2id hash |
| `currency` | String | Default `USD`. Used as the base currency for all monetary amounts |
| `budget_limit` | Decimal | Optional monthly budget cap; more than zero when set (D7) |
| `role` | String | `user` or `admin` (controls cross-user visibility) |
| `created_at` | Timestamp | Standard audit field |
| `updated_at` | Timestamp | Standard audit field |
| **IdentityLink** | A linked Google or Facebook identity, verified-email-gated (G9-G11). | User |
| **Receipt** | One purchase transaction, from one or more photos. | User |
| **LineItem** | One position on a receipt: product, quantity, unit price, total. | Receipt |
| **Category** | A spending classification. Either a system default or user-defined. | User (nullable for defaults) |
| **PositionMatch** | A decision that two line items are, or are not, the same physical purchase. | Receipt |
| **PositionMatchOverride** | A user correction flipping a same-item/two-items decision. Kept as labelled data (B7). | User |
| **MonthlySnapshot** | A finalised month: total, receipt count, and the count and value held out for review. A cache of derived data, taken on the first look after the month ends (ADR-0010). | User |
| **ExportJob** | One export of the user's receipts or statistics as CSV or JSON, written in the background: the filters it was asked with, its status, and where the finished file is stored (N6). | User |
| **Goal** | A financial or lifestyle objective the user declared. A financial goal is one of three kinds: a monthly spending ceiling, a savings target, or a cap on one category (F1). | User |
| **Recommendation** | Generated advice tied to a goal, with projected impact and user feedback. | User |

Relationships: a User has many Receipts; a Receipt has many LineItems; a LineItem has one
Category; a Goal produces many Recommendations; a User has many IdentityLinks; a User has many PositionMatchOverrides.

**Not yet groomed:** BR-7 (G1-G12, added by F0.10.1) is fully specified in the BRD, but
E1 as currently groomed (`docs/planning/backlog.yaml`) implements only G1-G7 —
registration, login, session refresh. G8 (admin role) and G9-G12 (OIDC linking) need
their own tasks before BR-7 is delivered; `IdentityLink` and `User.role` above describe
the target, not something built yet.

### Position matching rules (B1–B9)
- Comparing extracted items checks the name, unit price, quantity and total.
- If they match exactly, they are the same position (B2).
- The user can review and flip this decision (B7). When a user overrides a match, it calculates the new totals accordingly, and saves a `PositionMatchOverride` entity to capture this correction as labelled data.

## Receipt lifecycle

```
uploaded ──► parsing ──┬─► parsed          (counts toward budget)
                       ├─► manual_review   (excluded until resolved)
                       └─► failed          (parsing impossible)
```

`manual_review` is not an error state — it is a receipt that exists and is known to be
incomplete. It stays visible to the user and stays out of the arithmetic (A11, D3).

Deletion is terminal and physical, from any state. There is no `deleted` state and no
tombstone: the row, its line items and its stored photos are erased together, so a
deleted receipt cannot be listed, counted or recovered (ADR-0007).

## Invariants

Rules that must hold at all times. Each is a candidate for a test.

**Money and dates**

1. Monetary values are `Decimal`. Never `float` — binary floating point cannot represent
   currency exactly, and these numbers are shown to users as their own money.
2. A receipt belongs to the month of its **transaction date**, never its upload date (D2).
3. Timestamps are timezone-aware UTC. Month boundaries are derived, and a naive datetime
   silently shifts a receipt into the wrong month near midnight. A receipt's
   `transaction_date` is the exception in meaning, not type: it holds the time printed on
   the receipt, the shop's wall clock, stored unconverted. So a receipt belongs to the
   calendar month printed on it, and "the current month" is the user's, decided by their
   browser (ADR-0009). It is shown as printed too, read back in UTC rather than the
   browser's timezone, and correcting a receipt's date keeps its printed time of day.

**Aggregation**

4. A monthly total is the sum of line-item totals of `parsed` receipts in that month (D1).
5. Receipts in `manual_review` are excluded, and their count and value are reported
   alongside the total — the number is never quietly incomplete (D3). The value is the
   sum of their lines, since the printed total may be what could not be read. One with
   no readable date is reported in the month it was uploaded, so it always surfaces
   somewhere; a month's receipts list places it the same way, so list and total agree.
5a. A negative line printed under a product ("OPUST", a discount) is not a purchase.
   At upload it is folded into the nearest product line above it on the same photo:
   that line's `total_price` becomes what was paid, while its `unit_price` and
   `quantity` stay as printed, and the receipt still adds up to its printed total.
   Only a discount with no product above it stays a line of its own.
6. An in-progress month is always labelled incomplete wherever it is displayed (D4).
6a. Where the user has set a monthly limit, a month's spend is shown as a share of it
   (D7): rounded down, so a month under its limit never reads 100%, and not capped, so
   one over it reads past 100% with the amount over. The limit is presentation only:
   every month, finished or running, is measured against it as it stands now, and it is
   never stored in a snapshot, so changing it rewrites no finalised figure.
7. Snapshots are derived data. Any mutation of a receipt in a snapshotted month
   recalculates it (D6, N3): the flush that changes a receipt or one of its lines drops
   the snapshot of each month it touches, and the next look rebuilds it (ADR-0010). A
   month is snapshotted only once it has ended by the user's clock, and has ended
   somewhere on Earth. The month on screen refetches after every such change, so the
   new figure shows in the same session (F6.5).
8. Every date filter is a run of whole days, both ends included (E2, ADR-0012): the
   receipts list, the categorisation screen, the month view and the statistics all
   read "10 to 24 July" as the same fifteen days, bounded from midnight on the first
   day to midnight after the last, exclusive. A range ending before it starts is
   refused, never answered as empty.
9. Category statistics cover such a period, placed by
   the same date a month total uses and counting the same items: those on `parsed`
   receipts, with items on receipts under review named beside the figures, never
   silently dropped (E1, D3). Each category gets its total, its share of the period's
   spend to one decimal place and its item count — a "transaction" here is a line
   item, since one receipt spreads across categories — ranked by spend, ties by name
   (E4). A period whose spend is zero or less gives every share as 0.
10. A period is compared like for like (E3, D4). One starting on a 1st meets the same
   days of as many months before — 1-27 July meets 1-27 June, August meets July, a
   month's last day meets the other month's last day, a day the shorter month lacks
   falls back to its last — and the screen says so when the period stops mid-month.
   Any other period meets as many days immediately before it. Each category's change
   is its total less the previous one, and as a percentage of the previous total to
   one decimal place; a category new this period has no percentage (never a division
   by zero), and one spent on only before stays listed at zero, down 100%.
11. A period holding no receipts at all — of any status, filed by the same date — has
   no data, not a spend of zero (E5): it is answered with a receipt count of 0 and no
   totals, and shown as "No receipts in …", never as a table of zeroes. A period whose
   receipts are all under review is not empty: they are named, as invariant 5 says.
12. The statistics chart is worked out on the server (E6): a round scale whose steps
   are 1, 2, 2.5 or 5 times a power of ten, and each bar's height as a share of it, so
   the client draws what it is given and re-derives nothing. It draws the eight biggest
   categories in ranking order and counts the rest, which stay in the table; a bar for
   a period of refunds is drawn at zero rather than below the axis.
13. An export holds what the screen it was asked from shows (N6): the receipts list
   under its filters — CSV one row per line item, JSON receipts with their items as the
   list API returns them — or the statistics for the period, compared if the screen
   is, the JSON being exactly the statistics API's answer. It reads only its owner's
   data and is stored under their prefix; a spreadsheet cell that would run as a
   formula (a leading =, +, - or @) is written as text.

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
14. A correction the owner marks "apply to future items" creates a rule for later items
    with the same or a highly similar name from the same merchant (C5). Precedence:
    the owner's manual choice on a stored item, then a matching rule, then the
    categoriser under its threshold (ADR-0008).
14a. A user's own categories sit beside the built-ins and are offered to the picker and
    the categoriser as soon as they exist (C6). No two categories a user can see share a
    name, ignoring case. Built-ins cannot be renamed or deleted. Deleting one of the
    user's own moves its items, amounts unchanged, to a category the user chooses, never
    the deleted one. Its correction rules follow, unless the target is Uncategorized, in
    which case they are dropped (C7).

**Goals**

14b. A goal is financial or lifestyle, fixed once made; F9 depends on the split (F1).
    A financial goal names its kind and an amount above zero, and a category exactly
    when its kind is a category reduction. That category must be one the user can see.
    A lifestyle goal has no kind, amount or category: it is read through what is bought.
    Creating and editing a goal pass the same check (`app/domain/goals.py`).
14c. A lifestyle goal is projected onto spending when it is stated, and again when its
    name or description changes: the model chooses categories and item names it watches
    (F9, F8.2), from the categories the user can see only. A money goal never watches
    anything. Once the user corrects that list it is theirs, and no automatic pass
    overwrites it — the same rule as a manual category (13). A failed or slow model
    leaves the list empty, never the goal unsaved.

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

**Deletion**

24. Deleting a receipt erases its line items and every one of its stored photos; no
    orphaned object survives in storage (A12, N2).
25. Deleting a receipt discards the transient upload-job payload that named those
    photos, so no screen can ask for an image that is gone (A12).

## Open decisions

These are unanswered in the BRD (section 14) and block the epics named. Record the answer
here as an ADR when it arrives.

| Question | Blocks |
|---|---|
| Confidence thresholds for OCR, categorisation and manual-review triggers | Resolved — see ADR-0005 and `app.config.Settings.ocr_confidence_threshold` / `.categorization_confidence_threshold`; revisit once E3/E5 have real accuracy data |
| Whether budget periods are strictly calendar months or support custom cycles | Resolved — calendar months, see ADR-0009 |
| Whether thin history yields softened advice or none at all | E8 |
| Target values for the success metrics (section 12) | Not epic-blocking — informs tuning throughout |
| Which markets/currencies ship at launch, and whether multi-currency is truly out of scope | F1.4 |
| Whether household/shared budgets change the single-user assumption | Resolved — phase 2, see E12 in `docs/planning/backlog.yaml` |
