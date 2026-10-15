# ADR 0018: The per diem follows the Polish business-travel regulation, rates kept in code

**Date:** 2026-10-15
**Status:** Accepted — F20.4.1

## Context

A business trip owes the employee a per diem (*dieta*), and F20.4 works it out instead of
leaving the user to read the rules. Polish law sets it in one place:

- **The regulation.** Rozporządzenie Ministra Pracy i Polityki Społecznej z dnia 29 stycznia
  2013 r. w sprawie należności przysługujących pracownikowi zatrudnionemu w państwowej lub
  samorządowej jednostce sfery budżetowej z tytułu podróży służbowej. The consolidated text
  is Dz.U. 2023 poz. 2190.
- **Its amendments.** The only ones are Dz.U. 2022 poz. 1481 and 2302. The ELI register
  lists no others as of 2026-10-15, so the 2023 consolidated text is the text in force.
- **It binds private employers too.** It covers public bodies directly, and binds a private
  employer whose collective agreement, work rules or contract say nothing about travel
  (Kodeks pracy art. 77⁵ § 5). For the users of this product, an employee whose employer
  has not written its own rules, it is the rule.

Sources, read on 2026-10-15:

- The consolidated text and its annex:
  <https://api.sejm.gov.pl/eli/acts/DU/2023/2190/text.pdf> (also as HTML at `text.html`).
- The act's register entry, listing its amending acts:
  <https://api.sejm.gov.pl/eli/acts/DU/2013/167>.

## The rules as the regulation states them

- **The domestic rate is 45 zł** a day of travel (§ 7 ust. 1), in force from 2023-01-01.
- **A domestic trip of a day or less** (§ 7 ust. 3 pkt 1) earns:
  - nothing under 8 hours;
  - 50% from 8 to 12 hours;
  - the whole rate over 12 hours.
- **A domestic trip of more than a day** (§ 7 ust. 3 pkt 2) earns the whole rate for each
  24 hours. The part day left at the end earns 50% up to 8 hours and the whole rate over 8.
- **Meals provided free at home** (§ 7 ust. 4, 5) take off:
  - 25% of the rate for breakfast;
  - 50% for lunch;
  - 25% for dinner.

  This includes meals in the hotel price.
- **Time abroad** (§ 12) is counted from crossing the border on the way out to crossing it
  on the way back. By air, it runs from take-off at the last Polish airport to landing at
  the first one.
- **The rate abroad is the destination's**, in the annex's currency (§ 13 ust. 2, 4). It is
  earned in full for each 24 hours (§ 13 ust. 3 pkt 1). A part day earns (pkt 2):
  - a third up to 8 hours;
  - half over 8 to 12 hours;
  - the whole rate over 12 hours.
- **Meals provided free abroad** (§ 14 ust. 2) take off:
  - 15% of the rate for breakfast;
  - 30% for lunch;
  - 30% for dinner.

  Full board leaves 25% (§ 14 ust. 1), which the three meals together also give.
- **The travel within Poland on a trip abroad** follows the domestic rules (§ 21).
- **The settlement in złoty** is made at the NBP mid rate of the day the advance was paid
  (§ 20 ust. 2, 3).
- **The annex** sets the rate for 114 countries, plus one rate for "other countries"
  (41 EUR). A note under it covers three more places:
  - Gibraltar takes the British rate;
  - Hong Kong is 55 USD;
  - Taiwan is 40 EUR.

  The annex as amended applies from 2022-11-29.

## Decision

- **The rates are kept in code** (`backend/app/domain/per_diem_rates_pl.json`):
  - the domestic rate;
  - the annex by ISO 3166-1 country code;
  - the "other countries" rate;
  - `applies_from: 2023-01-01`, the first day both the 45 zł and the amended annex apply.

  A trip starting earlier gets no per diem (`per_diem_no_rates`). It is not given one at
  rates that did not apply to it. When the regulation changes, a new rate set with its own
  date is added beside this one, and a trip is matched to the set in force on its first
  day.
- **The calculation is a pure function** (`app.domain.per_diem`). It takes the times the
  user gives and returns one line per day. Each line carries the provision it follows and
  each reduction the meals that caused it. Nothing is guessed: a trip without times has no
  per diem.
- **What the user gives:**
  - the departure and return;
  - for a trip abroad, optionally, when the border or the last Polish airport was left and
    reached again;
  - the meals provided on each day of the main part.
- **Where the times are not given.** Without border times, a trip abroad counts as abroad
  throughout. This is the usual case by air from the home city, and it errs the user's way
  only by the hours to the airport.
- **The time at home on a trip abroad.** With border times, the hours at home on the way out
  and back are added together and earn the domestic rate as one stretch (§ 21). Meals at
  home on a trip abroad are not asked about.
- **Days are 24-hour stretches** counted from the departure, as the regulation counts them,
  never calendar days. Times carry their UTC offset, so hours across a clock change count as
  they were lived.
- **A meal never takes a day below zero.** The reduction is capped at what that day earned.
- **Into złoty, for now:**
  - a foreign per diem is shown in złoty at the NBP mid rate of the last working day before
    the return, through the same cached NBP port as receipts (ADR-0016);
  - once the trip records the advance's day (F20.5), its NBP rate is used instead, as
    § 20 names;
  - no rate leaves the złoty total empty instead of guessed.
- **Out of scope:** the overnight allowance and limits (§ 8, § 16), the local-transport lump
  sum (§ 9, § 15) and travel costs. They are reimbursed against receipts, which the trip
  already holds.

## Consequences

- **The rates go stale when the regulation changes.** Nothing tells the app, and checking
  ELI for amendments belongs to whoever maintains the rates file.
- **Each trip names its rules.** The per diem says which regulation it follows
  ("Dz.U. 2023 poz. 2190") and which paragraph each line follows, so a user, or the
  employer reading the settlement, can check it.
- **Several destinations are not handled.** A trip to two countries is counted at the trip's
  one destination. The regulation lets the employer name more than one (§ 13 ust. 2); that
  is left to a later change if users ask.
