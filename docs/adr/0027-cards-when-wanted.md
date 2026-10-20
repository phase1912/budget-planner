# ADR 0027: Cards when wanted, income on a card

**Date:** 2026-10-20
**Status:** Accepted — F23.21; supersedes ADR-0024's "every sum is on an account"

## Context

ADR-0024 put every sum on an account. A bill or an income named on none went on the
purchase card, and with no card one was opened by itself. That made bookkeeping the price of
entry. Someone who only wants to see whether a month fitted the budget still ended up with a
card, balances and a ledger they never asked for. Regular bills were also kept outside the
month's spending: they came off the income, never off the budget. So the budget that a
person without income set did not count their rent.

## Decision

- **Levels by what the user made, no switch.** A budget alone: receipts and bills against the
  monthly budget, no balance. A card: balances and what came off them. A business card: taxes
  and transfers. Home shows a balance only once there is one, and the Accounts screen invites
  a card without requiring it. Onboarding's card step can be skipped.
- **Income is bookkeeping, so it is always on a card.** An income or a regular income names
  its card or lands on the purchase card. With none, the request carries `new_card` (a name,
  optionally what is on it now), and the card is made with it. Without one the server refuses
  with `needs_card`. Every way income comes in asks for it in the same step: by hand, as a
  regular income, read off a payslip, confirmed from email, or approved from the assistant.
  The assistant names it "My card".
- **A new card counts from the income on, or from today.** At zero it counts from the
  income's day, so that income is on it. With what is on it now, it counts from today, and
  that sum is taken as already holding the income. A balance started before cards existed
  (F23.14) carries over, as before.
- **Bills need no card and are spending.** A bill on no card counts in the month's budget
  beside the receipts (`MonthSummary.bills`, a segment of Home's ring, a row in Spending). It
  never joins the receipts' `total` or the categories. Once there is a purchase card, it pays
  the bill. The ledger already read a sum on no account onto the purchase card. When a card
  stops being the purchase card, what it carried that way is written onto it, so its history
  never moves to the next card.
- **Removing the last card goes back to a budget alone.** The starting balance kept from
  before cards (F23.14) is cleared, so no balance comes back from it. The user's own
  regular incomes stop from next month: income has nowhere to land without a card. Past
  months keep what they had. Bills, receipts and the budget are not touched. The app says
  this before the last card is deleted.
- **Weekly as well as monthly.** A regular bill or income comes monthly on a `day` or weekly
  on a `weekday`. A month counts it as often as that weekday falls in the month, from its
  first day on; this is never an average. A change applies from this month, as any rule
  change does.

## Consequences

- Signing up and setting a budget is enough to use the product. Cards stay where they were,
  as the next step for those who want them.
- The budget now means everything spent: receipts and bills. A month with high rent shows
  less left than it did before this change.
- A weekly rule changed or skipped for a month (`set_occurrence`) stands in for that month
  as one sum, as a monthly one does.
- Existing data needs no migration. Incomes already on cards stay there, and bills on none
  keep landing on the purchase card as before.
