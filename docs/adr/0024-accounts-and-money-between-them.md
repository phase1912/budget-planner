# ADR 0024: Accounts and the money between them

**Date:** 2026-10-19
**Status:** Accepted — F23.15; extends ADR-0023

## Context

The balance (F23.14) was one figure carried from a starting amount. A family where one
partner runs a small business keeps money in several places: a business account that
sets tax aside and pays social contributions, a shared card for everyday life, savings.
It pays itself from the business account every month. One figure cannot say where the
money is, what of it belongs to the tax office, or what moved where.

## Decision

- **Accounts are optional.** Without any, income, bills and the balance work as before.
  With them, the balance is the sum of the accounts the user sees.
- **One ledger.** Every sum on an account becomes one `Entry` line. Balances, histories,
  "To check" and Home's balance are sums over the same list, so they never disagree.
- **Rules are read, not posted.** A regular income, bill or transfer is read for each
  month from the rule on its day. The user's change to one month's occurrence is stored:
  an income confirming it, or a move standing in for it (0 skips it). Nothing is written
  ahead, and stopping a rule never rewrites a past month. A rule made after its day has
  passed starts next month.
- **Tax lives on the account.** A business account has a rate. 5, 6 and 12 % are offered
  and any rate can be typed. Income from outside sets that rate aside, and it counts in
  the month at once, clean of the tax. Transfers are never taxed. Fixed sums such as ZUS
  are the account's bills. The user-level tax rule (F23.16) still applies to income that
  is on no account.
- **Purchases come off a purchase card.** This is the user's own marked card, else the
  family's shared one, which then pays for every member. A sum with no account of its own
  lands the same way. Choosing the card for each receipt comes later; the ledger already
  reads purchases per buyer, so it will only change where a receipt lands.
- **Closed months.** Only this month's entries change or go; earlier months keep what they
  hold. A late entry — a payslip for last month arriving now — is still added on its own
  date, as a bank books a late payment.
- **Sharing follows ADR-0023.** An account is its author's or the household's. A sum on
  a shared account is shared. A member who leaves takes their shared accounts back. A
  child moves nothing on a shared account.

## Consequences

- Reading a ledger computes from the opening day, which is fine at a family's scale. If
  that becomes slow, closed months can be snapshotted like `MonthlySnapshot`, because by
  this rule they never change.
- Another member's own money on a shared card shows only whose it is. Their private
  purchases show as one undated sum a month (ADR-0017).
- `incomes.source_id`, `incomes.tax`, `account_id` on incomes, regular incomes, bills and
  tax payments, and `income_sources.about` are added only (ADR-0014).
