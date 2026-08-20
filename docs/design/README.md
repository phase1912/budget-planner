# Design reference

What every phase-1 screen should look like, and the rules that hold them together.

Open `index.html` in a browser. The screens link to each other, so you can click through
the product as designed rather than reading files one at a time.

## This folder is the source of truth

When the built UI and a page here disagree, **the built UI is wrong** — a button of the
wrong colour, a radius that drifted, a state that renders zeros instead of saying there is
no data. Fix the code, not the reference.

That cuts both ways. When implementation shows the design is actually wrong, change the
files here **in the same commit** as the code — never as a later cleanup pass. This is the
same contract `docs/architecture/` already carries: a reference that is out of date is a
defect, not technical debt.

## What is where

| File | Role |
|---|---|
| `index.html` | The way in. Every screen, grouped by flow. |
| `design.css` | **The values.** Colour, radius, shadow, control anatomy — defined once. |
| `components.md` | The anatomy of each primitive in numbers, for checking code against. |
| `screens/*.html` | One file per screen. Plain HTML; no build step, no dependencies. |

`design.css` is what makes divergence checkable. Screens reference token names
(`var(--color-primary)`, `var(--radius-card)`) and primitive classes (`.btn--primary`,
`.card`, `.pill--warning`), never a raw hex. Layout specific to one screen stays inline in
that screen's file — only what more than one screen shares belongs in `design.css`.

## Screens

Sorted by the flow they belong to, not by file name.

| Screen | Route | Feature | BRD |
|---|---|---|---|
| `design-language.html` | — | F9.6 | DS-1 |
| `states.html` | — | F9.7 | A2, A11, A14, B6, D3, E5, F5, N2, N4 |
| `login.html` · `login-dark.html` | `/login` | F1.1 | N2 |
| `register.html` | `/register` | F1.1 | N2 |
| `profile.html` | `/profile` | F1.4 | D7 |
| `home.html` | `/` — no receipts yet | F1.1 | — |
| `dashboard.html` · `dashboard-dark.html` | `/` — once receipts exist | F6.7 | D1, D3, D4, D5, D7 |
| `receipts.html` | `/receipts` | *not yet in the backlog* | A13, N2 |
| `receipt-detail.html` | `/receipts/:id` | *not yet in the backlog* | A9, A12 |
| `upload-1-photos.html` | `/upload` | F2.6 | A1–A8 |
| `upload-2-extracted.html` | `/upload/review` | F3.7 | A9, A10, A11 |
| `upload-3-resolve.html` | `/upload/resolve` | F4.7 | A10, A14, B2–B4, B7 |
| `categorisation.html` | `/categories` | F5.7 | C3, C4, C5 |
| `categories.html` | `/categories/manage` | F5.6 | C6, C7 |
| `statistics.html` | `/statistics` | F7.7 | E1–E4, E6 |
| `goals.html` | `/goals` | F8.10 | F1–F9 |
| `dashboard-mobile.html` · `upload-mobile.html` | — | F9.6.2 | — |

Two rows say *not yet in the backlog*: browsing stored receipts came out of designing the
product and has no feature covering it. That gap is real and needs grooming.

## Decisions worth knowing before you build

Recorded properly in [ADR 0004](../adr/0004-ui-design-language-and-ingestion-flow.md);
the short version:

- **`/` is one route with two states.** `home.html` is what it looks like empty;
  `dashboard.html` is the same address once a receipt exists. Not two routes.
- **Upload is one flow in three steps.** Reading the receipt and sorting out overlapping
  photos are steps of it, not destinations. "Receipts" in the nav is the stored list.
- **One conflict queue.** Cross-photo duplicates, low-confidence fields and suspected
  duplicate receipts all queue together, with a counter, and nothing is stored while
  anything is open.
- **Separate `/login` and `/register`,** not budget-checker's tabbed modal — F1.5 needs a
  route table and a redirect on expiry, and a modal has no route to redirect to.

## Placeholders, not decisions

Things drawn to look complete that nobody has actually decided:

- **12-character password minimum** on `register.html`. F1.1.2 fixes the real rule.
- **Currency asked at sign-up.** The BRD does not say when. F1.4.2 locks it once a receipt
  exists, so asking early is kinder than asking late.
- **The full nav on every screen.** In reality each item appears as its epic lands — F1.1
  ships with Dashboard and Profile and nothing else.
- **Categories under Receipts on mobile.** Five nav items plus upload do not fit a bottom
  bar at 390px. Confirm before F9.4 fixes the shell.

## When the frontend catches up

`design.css` is not the shipped stylesheet. When F9.6.1 lands, its token values move into
`frontend/src/shared/styles/colors.css` as a Tailwind `@theme` layer, and F9.6.3 turns the
primitive classes here into real components. The values must match, and this file is what
they are checked against.

Do not copy markup from `screens/` into React. It is inline-styled artboard HTML written
to be read, and pasting it would break three rules in the `frontend` conventions at once:
tokens over literals, shared components over duplication, stores over data in markup.
Build the component properly and check it against the screen.

## Sample data

The numbers are the BRD's own, so figures agree across screens: PLN, July 2026, Fresh
Market, `Bananas 1kg` at 3.20, a 3 000 limit against 1 800 spent (60%). The Fresh Market
receipt of 20 July for 84.50 in the upload wizard is the same one the conflict step warns
is already stored, and the same one at the top of the receipts list. Keep it that way —
figures that contradict each other across screens make the reference untrustworthy.
