# ADR 0022: Design language v2 — palettes, tabs by what people do, one number first

**Date:** 2026-10-17
**Status:** Accepted

## Context

Compared with the budgeting apps on the App Store (Fleur, Bloomly, Spendee, Buddy,
Copilot; Billy, the Polish line-item app, rated 3.7), the product did more and looked
less: small type, grey cards, a sentence under every control, tabs named after records
(Receipts, Categories, Trips, Statistics, Goals) rather than after what people come to do.
The owner's reviewers — his wife first — turned the old design down and accepted a
canvas of new screens. ADR 0004's design language described the old look.

## Decision

- **Design v2** (`docs/design/v2.md`, `docs/design/screens/v2/`) replaces ADR 0004's look
  where they overlap; ADR 0004's flow decisions (one route `/`, the upload wizard's steps,
  one conflict queue) still hold.
- **Tabs:** Home · Spending · ＋ · Products · Plan, a bottom bar on a phone and a side menu
  on wider screens. Receipts become the history behind Spending, the categorisation queue
  a card on Home, trips Holidays in Plan, business trips shown only to someone who
  travels for work. Preferences become Settings. Old addresses redirect.
- **Six palettes,** Midnight (dark) by default, chosen in the first sign-in and in
  Settings and kept on the account; every palette restates the category colours its charts
  use, through the same tokens, so components never branch on the palette.
- **Type** is Manrope served with the app (the canvas's Plus Jakarta Sans lacks basic
  Cyrillic), on a larger scale (titles 28, rows 15,
  secondary 13); **geometry** is rounder (cards 22, hero 28, controls 16).
- **One number first** on every tab, as a ring or a big figure that changes view on a tap.

## Consequences

- Every screen built before F23 is re-laid in v2 without dropping a capability; a test
  that named the old layout is rewritten to name the behaviour.
- A font file ships with the client (no other origin, ADR-0020's consent rule holds).
- `docs/design/v2.md` is what the UI is checked against; the canvas is the drawing it
  came from, the files in the repository are the record.
