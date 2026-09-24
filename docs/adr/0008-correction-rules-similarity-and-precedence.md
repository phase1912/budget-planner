# ADR 0008: Correction rules — similarity measure and precedence

**Date:** 2026-09-24
**Status:** Accepted

## Context

BRD C5 says a correction applies to future items with "the same or highly similar
name" from the same merchant. The backlog (F5.5) adds that this needs a defined
similarity measure and an order of precedence against automatic classification.
Neither is in the BRD, and both constrain every later categorisation change.

Receipt names are OCR output. The same product shows up as "Protein Bar XL",
"PROTEIN BAR XL" or "Protein Bar XL." on different receipts, so exact matching alone
would make rules fire rarely enough that users stop trusting them.

## Decision

**Scope.** A rule belongs to one user and one merchant. Merchant and item names are
stored and compared normalised: lower case, surrounding whitespace trimmed, inner
whitespace collapsed (`app.domain.categories.normalise_name`). A receipt with no
merchant matches only rules made on a receipt with no merchant. There is one rule per
user, merchant and item name, and choosing again replaces it.

**Similarity.** `difflib.SequenceMatcher(...).ratio()` on the normalised names, with a
match at 0.8 or above (`RULE_NAME_SIMILARITY`). Among matching rules, the higher ratio
wins; on a tie, the newest rule wins, as the user's latest word.

**Precedence**, highest first:

1. A category the owner chose by hand on that stored item (`is_category_manual`) is never
   changed by any automatic pass (domain model invariant 13).
2. A matching correction rule. The categoriser is not consulted, so rules also work
   when no LLM is configured or reachable.
3. The categoriser, subject to the confidence threshold (ADR-0005); below it the item is
   Uncategorized (C3).

A rule-filed item stores no categoriser confidence, since no model scored it. A rule
whose category the user can no longer see is skipped, and the item goes to the
categoriser.

Rules apply at upload and when the owner re-runs categorisation on one receipt. They
are not applied retroactively across stored receipts.

## Consequences

- Short names at 0.8 can collide: "Milk 1L" and "Milk 2L" match. Such pairs almost
  always share a category, so we accept it. If real data shows otherwise, raise the
  threshold here, not at a call site.
- Different merchants never share rules, even for identical items. That is the BRD's
  wording, and it keeps one shop's quirks from leaking into another's.
- The rule set is loaded per upload job and matched in Python. That is fine at
  personal-finance scale. Thousands of rules per user would call for doing it in SQL
  (e.g. `pg_trgm`), which would need a new ADR to replace the measure.
