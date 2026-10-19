# Domain model and business rules

The entities, what they mean, and the rules that must hold. This is the global business
logic reference — when a rule here and the code disagree, one of them is a bug.

**Keep this document current.** A change to a business rule updates this file in the same
commit. Add the BRD requirement ID so the rule stays traceable to its source.

## Entities

| Entity | Meaning | Owned by |
|---|---|---|
| **User** | An account. Holds identity (`first_name`, `last_name`, `email`), currency, optional monthly budget limit, the token of their receipt forwarding address (F11.2), and a role (`user` or `admin`) — N2's per-user isolation applies to an admin exactly as to any other account (G8). | — |
| **User Attributes** | | |
| `id` | UUID | Primary key (generated via `gen_random_uuid()`) |
| `email` | String | Unique, used for authentication |
| `first_name` | String | User's first name |
| `last_name` | String | User's last name |
| `password_hash` | String | Argon2id hash |
| `currency` | String | Default `USD`. Used as the base currency for all monetary amounts; receipts in other currencies are converted into it (ADR-0016). Fixed once receipts exist (F1.4.2) |
| `budget_limit` | Decimal | Optional monthly budget cap; more than zero when set (D7) |
| `role` | String | `user` or `admin`: an admin opens the admin console (F18.6) and sees account facts, never receipts; super admins are `admin_emails`, not a role (ADR-0021) |
| `two_factor_secret` | String | The TOTP secret, encrypted (ADR-0021); in force once `two_factor_enabled_at` is set |
| `recovery_code_hashes` | JSON | SHA-256 of the unused recovery codes; a used one is removed |
| `created_at` | Timestamp | Standard audit field |
| `updated_at` | Timestamp | Standard audit field |
| **IdentityLink** | A linked Google or Facebook identity, verified-email-gated (G9-G11). | User |
| **Receipt** | One purchase transaction, from one or more photos or a forwarded e-receipt. Records the channel it arrived through (`photo`, `email`) and, for email, the message's Message-ID as its source reference (F11.1, F11.2). Carries its fiscal identity when one was read — the cash register's number and the receipt's number on it (F11.3, ADR-0015) — and, for an emailed receipt alike to a stored one, a mark naming that receipt until the user decides (F11.5). A receipt paid in another currency keeps its original currency, total and the rate it was converted at (F11.7, ADR-0016). | User |
| **LineItem** | One position on a receipt: product, quantity, unit price, total. Keeps the reader's confidence in it (F15.2) and, when its name is a remembered correction, what was printed (F15.3). | Receipt |
| **Product** | One thing the user buys, however each shop prints it: a name and, when printed, a package size in grams or millilitres (F16.1). Purchase lines link to it. | User |
| **ProductAlias** | One way a product is printed, as its matching key with an example; merging and splitting move these (F16.1). | Product |
| **ProductSelection** | Products the user explores together, saved under a name; follows merges and splits (F16.2). | User |
| **Trip** | A trip the user recorded, personal or business: a name, destination, whole days and purpose. Its receipts are those dated within it, unless moved in or out by hand (F20.1), its spending splits by each receipt's kind of expense (F20.2), and a personal one may have a budget (F20.3). | User |
| **NameCorrection** | A line name the user corrected on one shop's receipt — the printed name and what it means — applied to that shop's later receipts (F15.3). | User |
| **Category** | A spending classification. Either a system default or user-defined. | User (nullable for defaults) |
| **PositionMatch** | A decision that two line items are, or are not, the same physical purchase. | Receipt |
| **PositionMatchOverride** | A user correction flipping a same-item/two-items decision. Kept as labelled data (B7). | User |
| **MonthlySnapshot** | A finalised month: total, receipt count, and the count and value held out for review. A cache of derived data, taken on the first look after the month ends (ADR-0010). | User |
| **ExportJob** | One export of the user's receipts or statistics as CSV or JSON, written in the background: the filters it was asked with, its status, and where the finished file is stored (N6). | User |
| **Goal** | A financial or lifestyle objective the user declared. A financial goal is one of three kinds: a monthly spending ceiling, a savings target, or a cap on one category (F1). | User |
| **Household** | A group of users keeping one budget (E12, ADR-0017): a name, an invite code, an optional monthly budget. Reads its members' receipts, never owns them. | Its owner |
| **HouseholdMember** | A user's place in a household, as `owner` or `member`. One household per user. | Household |
| **PlanGrant** | A plan an admin gave the account from one moment to another, with the reason and who gave it; taken back by setting `revoked_at`, never deleted (F18.6.3, ADR-0021). | User |
| **AdminAction** | One thing an admin did to an account, for the log super admins read (F18.6.3). Survives either account's deletion with that side emptied. | — |
| **Recommendation** | Advice on one goal: the category, recurring purchase or priced product it targets, what to do and why. Asking again replaces the goal's advice, except advice the user marked won't-follow or not helpful (F8.9), which stays. Carries its projected impact (F8.5). | User |

Relationships: a User has many Receipts and belongs to at most one Household; a Receipt has many LineItems; a LineItem has one
Category; a Goal produces many Recommendations; a User has many IdentityLinks; a User has many PositionMatchOverrides.

**Not yet groomed:** BR-7 (G1-G12, added by F0.10.1) is fully specified in the BRD, but
E1 as currently groomed (`docs/planning/backlog.yaml`) implements only G1-G7 —
registration, login, session refresh. G8 (admin role) is built by F18.6 (ADR-0021);
G9-G12 (OIDC linking) need their own tasks before BR-7 is delivered; `IdentityLink`
above describes the target, not something built yet.

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

4. A monthly total is the sum of what was paid for the line items of `parsed` receipts in
   that month (D1): each line's total less its share of an unprinted discount (5d).
5. Receipts in `manual_review` are excluded, and their count and value are reported
   alongside the total — the number is never quietly incomplete (D3). The value is the
   sum of their lines, since the printed total may be what could not be read. One with
   no readable date is reported in the month it was uploaded, so it always surfaces
   somewhere; a month's receipts list places it the same way, so list and total agree.
5a. A discount printed under a product ("Rabat", "OPUST" and the like) is read as a line
   of its own with a negative total, where it was printed, so a receipt's lines add up
   to what was actually paid. It takes the category of the nearest product above it on
   the same photo (`app/domain/discounts.py`). Otherwise that category would read
   dearer than it was and Other would go below zero. A discount with no product above
   it keeps whatever category it was given. Subtotals, the sum of discounts, VAT tables
   and payment lines are not lines.
5b. A receipt's lines agree with its printed total when they differ by at most one
   grosz (0.01, `app/domain/receipt_totals.py`). Weighed goods and per-line rounding
   leave that much, and it is no reason to hold a receipt out of the month. Anything
   more is a misread line, and the receipt waits in `manual_review` until it is
   corrected (A9, A11). The receipt says why wherever it is shown. When its lines come
   to more than was paid, the reader most likely missed a discount: the user is
   offered that exact amount as one "Rabat" line, and adding it is their call, never
   automatic. That line is filed under the receipt's dominant category, the one most
   was spent on, because it reduces the bill rather than one product. When the lines
   come to less, a line is missing or misread, and only the user can correct it.
5c. Before a disagreeing receipt reaches the user, the app tries to make it agree
   itself (`app/domain/receipt_reconciliation.py`, `ReceiptService._reconcile_total`).
   The total read is the amount paid ("DO ZAPŁATY"), deposits on returnable packaging
   (kaucja, Poland since October 2025) are lines of their own, and a deposit handed back
   is a negative line. Rules come first, each applied only if it closes the gap exactly:
   the goods subtotal taken instead of the amount paid while the deposit is a line; a
   discount read without its minus; a deposit or footer subtotal listed twice (never two
   equal products — those are two purchases); one line whose total is not its quantity
   times its price. Then the model reads the photos again, up to twice, told how far off
   the last reading was; a new reading is kept only if its lines agree with the same
   total, so the model can never "fix" a receipt by rewriting what was paid. Only what
   still disagrees is shown to the user, marked as already tried (`total_reconciled_by`
   = `unresolved`), with 5b's offer.
5d. A discount the receipt does not print — a gift card, a voucher, a deal at the till —
   is stated by the user as an amount off the receipt (F23.7, `app/domain/discount.py`).
   It is spread over every line in proportion to what each cost, or over the lines the
   user picks; shares are cut to the grosz and the pennies left go to the dearest line, so
   they sum to the amount exactly. Each line keeps its printed total, so price history
   shows the shelf price, while every spending figure — month, category, trip,
   household, statistics, exports' totals — counts `paid` (total less share). A discount
   larger than the lines it is spread over is refused (`discount_too_large`). Correcting
   the lines spreads it again over all of them, or drops it if it no longer fits.
5d. A receipt with no readable date is dated the day it was uploaded (UTC), marked as
    assumed, and stored like any other; a missing date never holds it out of the month
    or stops the upload (`app/domain/receipt_dates.py`). The wizard says the date was
    assumed and lets the user change it before storing; after storing it is changed
    from Edit like any date. Only a missing total still needs the user (5b, A11).
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

**Duplicate receipts**

11a. A receipt's fiscal identity is its register number and its receipt number, both read
    and normalised to letters and digits; half of one identifies nothing. A receipt whose
    fiscal identity matches one the user already has is the same receipt, whichever
    channel brought it: it is never stored again — the wizard says so and when the first
    was added, and email drops it (F11.5).
11b. Without a fiscal match, a receipt with the same merchant, date and total as a stored
    one is only likely the same: the wizard asks, and an emailed one is stored with the
    mark until the user keeps both or removes it. Two receipts whose fiscal identities
    are both known and differ are never likely duplicates (A14).
11c. A receipt the user skipped as a duplicate is never stored (A14).

**Foreign currency** (ADR-0016)

11d. Every stored amount is in the account's currency (D1). A receipt paid in another is
    converted when it is stored, at the NBP mid rate of its purchase date or the last
    published before it, crossed through the złoty, the ECB's as fallback (F11.7). It
    keeps its original currency, total, the rate, its date and source; the rate is never
    looked up again, so a stored month never shifts.
11e. Converted line totals add up to the converted total whenever the printed ones added
    up to the printed total: the rounding cent goes on the largest line (A9).
11f. A foreign receipt no rate is found for is held in review in its printed amounts, never
    counted as if it were in the account's currency (A11, D3). Amounts the owner then
    corrects are in the account's currency, and the rate they imply is recorded as manual (F11.7).

**Households** (ADR-0017)

11g. A receipt is only ever written by its owner. Membership of a household grants read
    access to the other members' receipts that are not private, and nothing else; leaving
    or removal revokes it at once (N2).
11h. A private receipt counts in the household's totals and budget, but the household sees
    only one sum per member per month, never its merchant, items, category or date (N2).
    The household's day-by-day chart therefore places a private receipt on its day only
    for its owner; for the others the period's private spending is one undated sum.
11i. A user belongs to at most one household, and its members share one account currency,
    in which its totals are (D1).
11j. A household's month is the sum of its members' months, counted by the same rules (D1-D3),
    private receipts included as money, against the budget its owner sets (D7). It is
    always computed live, never snapshotted: a member who leaves takes their receipts with
    them (F12.5).
11k. An account with no receipts yet takes the household's currency when it joins, as it
    could on Profile; one with receipts in another currency is refused (F12.3, D1).

11l. Each line keeps the reader's confidence in it. A line below
    `ocr_confidence_threshold` is doubtful: marked "check this" in the wizard and on the
    stored receipt, never silently accepted (A10, F15.2). A line the user corrects is no
    longer doubtful; one stored before scores were kept, or typed by hand, has none.

11m. A line the user renames on a receipt from a known shop is remembered: that shop's
    later receipts read the same printed name, ignoring case and spacing, as the user's
    name, before they are categorised. The printed name stays beside it, and the line can
    be put back, or the correction forgotten for the shop. A near match is never renamed:
    it may be another product (F15.3).

11n. A receipt is user-corrected when the user changed what was read — a line, the
    total, the date, the shop — or added a line the reader missed, in the wizard or after
    storing it; such lines are marked too. A name fixed by a remembered correction is not
    a user correction: it is counted apart as reading that worked. The reading-accuracy
    report counts these over the months receipts were read in, never across users (F15.4).

11o. A product is the user's own: lines are matched only to their products. A line
    printed a way already known joins that product; a name that abbreviates a known one
    word for word, of the same size, joins it too; a name merely alike is asked of the
    model, and otherwise starts a product. Different sizes, article numbers or
    varieties are never matched by rule. Discounts and zero lines are not products.
    A date or billing period printed in a name (month names, years, `01.11.2026`) is not
    part of the product, so a monthly subscription stays one product; products that were
    told apart only by such a date are merged into the most bought one.
    Merging folds products into one that keeps its name; splitting takes one way of
    printing, with its lines, into a product of its own. Both hold for later receipts
    (F16.1). The user may rename a product: only the shown name changes, matching still
    goes by how receipts print it, so later receipts find it under the new name.

11p. Exploring products counts only counted receipts — the month's own rule (D3) — by the
    purchase day, else the upload day, over whole days (ADR-0012). Quantities are kept
    apart by kind and never added across: pieces, grams, millilitres. A price is per kg or
    l where the product's size is printed, else per piece. A shop's price is compared with
    the cheapest on the latest prices; shops are one ignoring case and spacing. A price
    change runs from the period's first purchase to its last (F16.2).

11q. A product is cheaper elsewhere when, among prices no older than
    `price_freshness_days`, another shop's latest price for one item is below the latest at
    the shop it was last bought in; nothing is said when that shop already was the cheapest, or when
    fewer than two shops have a recent price (F16.3).

11r. A receipt is on a trip when the user put it there by hand, or, unless moved by hand,
    when its purchase day falls within a personal trip's days, both ends included. A
    business trip holds only what the user put in it: a purchase on one may be the user's
    own, so its days only ask about the receipts within them — the upload wizard asks
    before storing, an upload started on the trip's page answers for it, and one that came
    by email waits on the trip's page — and an unanswered receipt counts in the user's
    budget. One user's trips never share a day, so a receipt is on one trip at most. A personal trip's
    receipts count in the month, its limit, statistics and advice as before, and are shown
    apart; a business trip's are the employer's money and count in none of them — nor in
    the household's totals, nor as held out for review. Deleting a trip gives its receipts
    back to their dates. A finished month's snapshot is not recomputed when a trip is
    recorded later (ADR-0010) (F20.1).

11s. Every receipt has a kind of expense — transport, accommodation, meals or other —
    guessed by the same reading that finds its shop and lines and kept with it; one read
    before kinds were guessed takes the kind holding most of its money by its lines'
    categories (Transport, else Dining and Groceries as meals, else other). The user's
    choice wins over the guess and over any later reading, until given back. A trip's
    spending splits by kind, every kind shown even at zero, in the account's currency, and
    by the currency each receipt was paid in, as printed; only read receipts count, as in
    its total (F20.2).

11t. A personal trip may have a budget of its own, in the account's currency; a business
    trip has none — its money is the employer's. What is left is the budget less the trip's
    total, and goes below zero once overspent. A trip reads as a story from its read
    receipts only: what each of its days cost, a day without spending at zero, and what
    each category took, the largest first. The month still counts the personal trip's
    spending as before (F20.3).

11u. A business trip's per diem follows the Polish business-travel regulation (Dz.U. 2023
    poz. 2190; ADR-0018), worked out only from the times the user gives — never guessed —
    in 24-hour days from the departure: at home 45 zł a day, a day or less earning nothing
    under 8 hours, half to 12, all over 12, and a part day after full ones half up to 8
    hours; abroad the destination's rate in its currency, a part day a third up to 8 hours,
    half to 12, all over 12, with the hours at home on the way counted at the domestic rate.
    Meals provided take 25/50/25% of the rate at home and 15/30/30% abroad, never a day
    below zero. A trip before the rates kept has none. Its złoty sum uses the NBP mid rate
    of the day the advance was paid (§ 20), or without an advance of the last working day
    before the return, or is left empty without one (F20.4, F20.5).

11v. A business trip may record the advance the employer paid, in the account's currency,
    and its day; a personal trip has none. Its settlement is expenses + per diem − advance
    in the account's currency — negative when the employee hands some back — and stays
    open, never guessed, while a claimed per diem cannot be converted. It is written for
    the employer as a PDF carrying each receipt's photos, or as CSV, in the user's
    language, from the trip's read receipts only (F20.5).

11w. An expense with no receipt — cash for a tour, a tip — is typed in and stored as a
    receipt of one line through the `manual` channel: read, its category the user's, a
    foreign one converted like a read receipt (ADR-0016). It counts wherever a receipt
    counts — the month, its limit, statistics, goals, a trip by its date — never in the
    reading-accuracy report, since nothing was read, and the settlement marks it as having
    no document (F20.5).

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
15a. The evidence advice cites is gathered from the owner's parsed receipts only, over
    the running month and the two before it (`app/domain/goal_analysis.py`, F2). It
    names the highest-spend categories and the largest increases by amount against the
    like-for-like period before. It also names the purchases that recur, meaning they
    appear on at least two receipts. Receipts are counted, not lines, and each purchase
    names the shop whose receipts carry it most ("9 of your 14 Fresh Market receipts").
    Those purchases are narrowed to what the goal concerns: a lifestyle goal's watched
    categories and keywords (a keyword matches any name containing it), a category
    reduction's one category, or all spending for a ceiling or savings target. A
    lifestyle goal watching nothing has no purchases to cite.
15b. The evidence also names the prices of the products the goal concerns (F16.4): where
    one recently cost less than at the shop it was last bought in (11q), and a rise of 5%
    or more over the window, each with how many a month the user buys. At most ten,
    those a shop switch saves most on first.
15c. A recommendation is kept only when its target is a category, recurring purchase or
    priced product the analysis names (`app/domain/advice.py`, F3). The model's wording is not
    trusted to be specific: a target outside the evidence is generic by definition and
    is dropped, so a goal may end up with no advice rather than generic advice. A
    model that gives no answer leaves the goal's earlier advice in place and is
    reported as unavailable, never as "no advice".
16. Every recommendation quantifies its projected impact, computed from real history
    rather than asserted by the model (F4). The model only says what share of the
    spending on its target the action removes (100% to stop, 50% to halve). The
    monthly saving is that share of the target's spend in the analysis window, divided
    by the window's length in average months (`app/domain/advice.py`,
    `project_impact`). For a recurring purchase, the purchases avoided a month are
    worked out the same way from the receipts that carried it. A product with a cheaper
    shop saves the price gap for one item times the items bought a month, on the share
    of purchases moved there (F16.4). The model is told never to state a saving.
17. Below the minimum history threshold, the system says more data is needed and produces
    no recommendation (F5). The threshold has two parts and both must be met: at least
    `min_receipts_for_advice` parsed receipts (4 by default), and at least
    `min_history_days_for_advice` days (30, BRD F5's "one full month") from the first of
    them to today. Receipts held out for review or still being read count toward
    neither. The check runs before any model is asked; until it passes, the goal's card
    shows how far there is to go instead of a button to ask (`app/domain/advice.py`).
18. When spend is on track, report progress and suggest nothing (F6). On track applies
    to goals that cap a month's spend, a spending ceiling or a category reduction: this
    month's spend so far, counted like the month view, carried forward at the same daily
    rate to the month's end, finishes at or under the cap (`app/domain/goal_pace.py`).
    Such a goal gets no advice and loses the cut advice it had, without the model being
    asked. Its status is worked out live on every look and never stored, so it cannot
    say "on track" after the month has turned.
18a. A monthly money goal is at risk when the same pace heads over its cap after the first
    week of the month (F7); earlier, one big shop is most of the evidence. At risk is
    worked out live, never stored, and shown on the dashboard and Goals without being
    asked for, with how far over the month is heading. A background pass gives each goal
    at risk advice to cut back if it has none from this month, so the warning arrives
    with a way to correct course; advice already given this month, asked for or not, is
    left alone. The user may set a goal's warning aside, which holds until the month ends.
18c. A receipt forwarded by email (F11.2) is read only when it was sent to a live
    forwarding address, from that user's own account email, within 20 emailed receipts
    a UTC day; anything else is dropped and never stored. It skips the upload wizard,
    is categorised with the user's rules like an upload, and lands in review when the
    read is uncertain or fails. The same Message-ID is one receipt however often it is
    delivered. Replacing the address invalidates the old one at once (ADR-0013).
18b. The user may mark a recommendation won't-follow or not helpful, and undo the mark
    (F8.9). A marked recommendation survives later refreshes of its goal's advice and
    stays visible, struck through. Every later ask is told what was turned down and not
    to repeat it; since that is only a request to the model, fresh advice on a target
    the user turned down is also ranked after the rest (`demote_dismissed`), never
    dropped. Undoing a mark makes the advice ordinary again, replaced on the next ask.

**Identity**

19. Login and registration return an identical generic error whether the email is
    unknown or the password is wrong (G2, G4).
19a. A new password has at least 8 characters, a letter, a digit and a special
    character, and is not a common password (G1, `app/domain/passwords.py`). The
    registration screen ticks each rule off as it is met, and a refusal names the rules
    the password lacks — unlike a taken email, which stays generic (19).
20. Refresh tokens rotate on use; presenting one already exchanged revokes every token
    issued from that session (G5, G6). A session left unused ends 30 days after its last
    refresh; however often it is used, it ends 90 days after sign-in.
20a. An account opens unconfirmed and stays so until its owner follows the link mailed
    to the address (F17.8.2). Until then it may look around and type in expenses, but
    not upload receipts, have forwarded receipts read, or start or invite to a household.
    Accounts that existed before confirmation were marked confirmed.
20b. Throwaway addresses (the list in `app/domain/disposable_email_domains.txt`, any
    subdomain of one included) and domains DNS says receive no mail cannot open an
    account or become an account's address; when DNS cannot be asked, the address is
    accepted (F17.8.4).
20c. A password reset link works for one hour and once, and is asked for with an answer
    that never tells whether the address has an account. Setting the password ends every
    session of the account and confirms its address. A new address takes effect only
    when the link sent to it is followed; the old address is then told (F17.8.3).
20d. An account opens only with the terms and privacy policy accepted; when, and which
    version (`app/domain/terms.py`), is kept on it (F17.9.4).
20e. Deleting an account, confirmed with the password, deletes every row of the user's —
    each references the account with ON DELETE CASCADE — and their files under
    `receipts/{id}/` and `exports/{id}/`. In a household, an owner's place passes to the
    member who joined first; the last one out dissolves it (F17.9.1).
20f. Receipt photos are kept 90 days, exports 7 (F17.9.3), then storage deletes them by
    lifecycle rule; the lines and totals read from a photo stay, and the receipt says its
    photo is gone. A trip's settlement after that is its summary without the photo pages,
    the receipt marked "photo removed after 90 days". A photo is kept as a JPEG of at most
    2000 px once it has been read (`app/domain/retention.py`).
20g. The service's own analytics records a signed-in user's actions — signing up,
    confirming, signing in, a day of use, uploading and storing a receipt, exporting —
    against the account, with the time and nothing more, for 12 months (F17.3.1); visits to
    the public pages are only counted per day, page and source, never with anything that
    identifies the visitor (F17.3.2). A visit is the first public page of a page load, and
    its source is where that page was reached from; a signed-in reader is not a visitor.
    Only admins read the totals, never one user's data, and admins are in none of them.
20h. A super admin is an address in `admin_emails`; an admin is `role = admin`, appointed
    and removed only by a super admin, and no one changes a super admin through the
    service. Admins see an account's facts, plan and activity, never what it stored (N2);
    they confirm its address and send it links, never set its password; every action is
    in the admin log, read by super admins (F18.6, ADR-0021).
20i. With two-factor sign-in on, the password alone opens no session: it gives a
    five-minute challenge that an authenticator or recovery code exchanges for one. An
    admin page refuses a session opened without a second factor wherever the deployment
    requires it; a session keeps the mark across refreshes. A recovery code works once
    (F18.6.1).
20j. The plan in force is the paid plan while a grant runs that is not taken back, else
    free. A grant made while a plan runs starts when it ends, and the plan runs on through
    grants that follow without a gap (`app/domain/plans.py`, F18.4).
21. An OIDC identity links to an existing account only when the provider reports a
    verified email matching it; an unverified email never links automatically (G10, G11).

**Limits**

21a. Every receipt read costs a model call, so reads, not stored receipts, are limited
    (F10.6, `app/services/quota.py`). An account may have its plan's receipts read per
    calendar month in UTC — `monthly_receipt_quota` on the free plan (10 by default),
    `paid_monthly_receipt_quota` on the paid one (200), which is also ad-free (F18.4): each
    receipt in an upload counts when the upload is accepted, stored later or not, and so
    does each e-receipt that arrives by email. An upload that would go past it is refused
    before anything is read, saying the limit and the date it resets; an e-receipt past
    it is dropped. All non-admin accounts together may have at most
    `daily_receipt_read_ceiling` receipts read per UTC day (100 by default), whatever
    their own quotas say. An admin — role `admin`, or an email in `admin_emails` — has
    neither limit and no wider access to data (N2, G8).
21b. Registration, upload, asking for advice and export are also limited per client IP,
    as login already was; a limit hit is a 429 that says when to try again.

**Access**

22. Every query for a user-owned entity is filtered by owner (N2).
23. A request for another user's record returns 404, not 403 (N2).

**Deletion**

24. Deleting a receipt erases its line items and every one of its stored photos; no
    orphaned object survives in storage (A12, N2).
25. Deleting a receipt discards the transient upload-job payload that named those
    photos, so no screen can ask for an image that is gone (A12).

**Income and balance**

26. A month's income is the sum of the entries received in it (F23.10). With none
    entered, the account's usual income stands in, marked as usual rather than entered,
    so "left to spend" is right on the 1st; with neither, the month has no income figure
    (`app/domain/income.py`). Each entry has a kind (salary, side, refund, other) and says
    whether it was typed or read from a document.
27. The balance is a starting amount the user states once — what the accounts hold on a
    date, not income — carried forward: plus income received since, minus spending
    counted since by invariant 4's rule (F23.14, `app/domain/balance.py`). Without a
    starting amount there is no balance, never a zero.
28. Income, its entries and the balance are their owner's alone; a household sees none of
    them (N2, ADR-0017).
29. Accounts made before the first-sign-in setup existed count as having done it
    (F23.9); only new accounts are walked through it, once, on any device.
30. From payday on (31 meaning a month's last day), a running month with no income
    entered asks once whether the salary came; confirming records the usual income as
    received that day. A balance at or below zero asks for missing income or a new
    starting amount rather than showing a debt: it almost always means income not
    entered.
31. Income read off a document — a payslip or transfer confirmation (F23.11) — is never
    stored as a file or written as an entry by itself: it is read in memory, shown as a
    draft, and only what the user confirms becomes an entry, marked as from a document
    (correcting it later keeps that mark). A document that is not money received is
    refused. A payslip or transfer forwarded by email is told apart from a receipt by the
    reader itself (`document_kind`, or a low `is_receipt_confidence`): it becomes a
    pending income — kept apart from entries, counting nowhere — and its stored files are
    deleted; confirming makes it an entry, dismissing drops it. A letter delivered twice
    waits once.

33. Regular incomes (F23.17) — a salary, a side job, a pension — are set once and count in
    every month from the month they were added, as they reach the account; anything else
    is entered on top by hand, through ＋ or from a document. With any regular income the
    single usual income no longer stands in. Ending one stops it from the next month and
    keeps it in the months it ran (one ended in its first month simply goes). The balance
    gains each on its day of the month (a 31st in a shorter month on its last day).
34. A user who pays their own taxes (F23.16) sets a rate and an optional fixed sum a
    month. Each income — entry or regular — says whether the tax comes out of it: by
    default earnings do and gifts, refunds and sales do not; a regular income is untaxed
    until ticked, and income read off an emailed document asks the user to decide. A
    month's taxes are the rate on its taxed income plus the fixed sum, once; "left to
    spend" counts the income after them. Taxes paid are recorded apart: they lower the
    balance and what is still owed, never the spending.

35. Regular bills (F23.18) — rent, a subscription, a loan — go every month without a
    receipt, from the month they were added, and stop like regular incomes do. They are
    not purchases: they never enter a month's spending total, categories or statistics,
    but they come off what is left of the income on Home and in Plan ("spent · bills ·
    free"), off the balance on their day, and off what a savings goal can count on.

**Goals before they are saved**

32. A money goal is checked against the user's last three whole months that had receipts
    (F23.13, `app/domain/goal_check.py`): a ceiling against the monthly spend, a category
    cut against that category's, a savings target — a sum put aside each month —
    against what is usually left (income minus spending). Within it: doable. Beyond it:
    a stretch by the difference, with up to three categories it could come from, each
    trimmed by 15 % of its monthly spend, and the total those trims make even when it
    falls short. No months with receipts, or a savings target without any income: not
    checkable. The check advises; it never stops a goal being saved.

## Open decisions

These are unanswered in the BRD (section 14) and block the epics named. Record the answer
here as an ADR when it arrives.

| Question | Blocks |
|---|---|
| Confidence thresholds for OCR, categorisation and manual-review triggers | Resolved — see ADR-0005 and `app.config.Settings.ocr_confidence_threshold` / `.categorization_confidence_threshold`; revisit once E3/E5 have real accuracy data |
| Whether budget periods are strictly calendar months or support custom cycles | Resolved — calendar months, see ADR-0009 |
| Whether thin history yields softened advice or none at all | E8 |
| Target values for the success metrics (section 12) | Not epic-blocking — informs tuning throughout |
| Which markets/currencies ship at launch, and whether multi-currency is truly out of scope | Resolved — any account currency; foreign receipts converted at NBP rates, see ADR-0016 |
| Whether household/shared budgets change the single-user assumption | Resolved — receipts stay their owner's, a household only reads them, see ADR-0017 |
