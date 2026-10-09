# ADR 0016: Foreign receipts are converted at the National Bank of Poland's rate of the purchase date

**Date:** 2026-10-09
**Status:** Accepted — F11.7.1; reverses the BRD's multi-currency non-goal (section 4.2)

## Context

The BRD assumed one currency per account and put conversion out of scope. In practice the
reader recognises the currency printed on a receipt and the app then dropped it: a
Ukrainian receipt for 1197 UAH was counted as 1197 PLN on a złoty account, overstating the
month about tenfold. Users travel, and an account may be in any currency, so the fix
needs a rate source that is free, needs no key, and covers any pair a user can meet.

Checked on 2026-10-09:

- **NBP (api.nbp.pl)**, free and keyless. Table A, published every working day, has 32
  currencies including UAH, USD and EUR; table B, published on Wednesdays, has about 116
  more (VND, for one). Rates are mid rates in złoty. A day without a table — a weekend,
  a holiday — answers 404; a date range answers every table in it.
- **Frankfurter (the ECB's reference rates)**, free and keyless, about 30 currencies and
  **no UAH**. A date without rates answers the last one before it.

## Decision

- **Source.** NBP first, table A then table B. Every NBP rate is in złoty, so any two
  currencies NBP covers are converted by crossing through it: UAH → USD is the UAH mid
  divided by the USD mid. Frankfurter is the fallback, used only when NBP cannot answer —
  it is down, or lacks the currency; it never answers for UAH.
- **Rate date.** The purchase date — the printed date, else the upload date the receipt is
  filed under (BRD A11). When no table was published that day, the last one before it,
  looking back at most 14 days, which spans a table B week and a long holiday.
- **Rounding.** Amounts are converted to two places, half up. Line totals are converted
  one by one and the rounding remainder is put on the largest line, so lines that added up
  to the printed total in the receipt's currency still add up to it in the account's.
- **What is stored.** The receipt keeps its original currency, its original total, the
  rate, the date it was published for and its source. Its total and line amounts are in
  the account's currency, so every total, statistic and budget figure stays in one
  currency (BRD D1). The rate is never looked up again, so a stored month never shifts.
- **When.** At storing, through the wizard or by email. The wizard shows the conversion
  before the user stores. A receipt for which no rate can be found is stored in its own
  amounts but held in review saying why, never counted as if it were in the account's
  currency (BRD A11, D3).
- **Cache.** Each rate fetched is kept in the database by pair and date, so a month of
  receipts costs a handful of calls and a rate source being down later costs nothing.

## Consequences

- Any currency NBP publishes converts into any other, so a złoty, dollar or hryvnia
  account all work; a currency neither source has (rare) leaves the receipt in review.
- Conversion uses mid rates, not what the card was charged. The figure is an estimate the
  user can trace back, which is enough for a budget; it is not an accounting record.
- The account currency still cannot change once receipts exist (F1.4.2): stored totals
  are in it.
- The BRD's non-goal "multi-currency conversion" is reversed for receipts. Budgets, goals
  and advice stay in one currency per account.
