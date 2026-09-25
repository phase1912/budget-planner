# ADR 0009: The budget period is the calendar month of the receipt's printed date

**Date:** 2026-09-25
**Status:** Accepted

## Context

BRD section 14 leaves open "whether budget periods are strictly calendar months or
support custom cycles", and the domain model lists it as blocking E6. F6.1, the first
monthly figure, cannot be built without an answer, and neither can anything after it:
the month-to-date label, snapshots, the limit percentage and E7's statistics all count
per period.

A second question comes with it: in whose timezone does a month begin? A purchase at
00:30 on 1 October in Warsaw is still 30 September in UTC. CLAUDE.md and the domain
model require timezone-aware UTC timestamps. Looking at how receipts are stored changes
the question, though. The parser reads the date and time printed on the receipt, the
shop's own wall clock, and the repository stores them unconverted, labelled UTC:
"14.09.2026 13:08" becomes `2026-09-14T13:08Z`. The stored value is local time in a UTC
envelope.

## Decision

**Calendar months.** A period runs from the 1st to the last day of the month, as D2
already says ("within that calendar month"). Custom cycles such as payday to payday
are not supported. `app.domain.budget.BudgetMonth` is the type, with an exclusive end
bound so no day is lost at the edges.

**A receipt belongs to the month printed on it.** Months are bounded on the stored
`transaction_date` as it is, with no timezone conversion. Converting it into the user's
timezone would count the shop's local time twice: a receipt printed at 23:30 on 30
September would move to 1 October in Warsaw.

**"Now" is the user's clock.** Which month is current, and so where the month switcher
stops, is decided by the browser from its local date and passed to the API as an explicit
year and month. The server never infers the user's current month from its own UTC clock.

## Consequences

- No timezone is stored per user yet. F6.4 needs one: it must decide on the server when
  a month is over, to finalise its snapshot. That is where a user timezone setting
  belongs, and the backlog already puts "across user time zones" there.
- If receipts ever gain a real UTC instant, say from a payment integration with its own
  timestamps, the "stored value is local time" premise breaks. Those would need their
  local date recorded explicitly, rather than this ADR quietly ceasing to hold.
- Supporting custom cycles later means replacing `BudgetMonth` with a period type. Every
  consumer goes through that one type, so the change stays local.
