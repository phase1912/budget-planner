# ADR-0004 — A UI design reference in the repository, and the shape it fixes

- **Status:** Accepted
- **Date:** 2026-08-20

## Context

Every phase-1 screen was designed before any of them was built. That produced two
problems worth deciding once rather than per feature.

The first is storage. A design that lives in a chat log, a screenshot or a hosted canvas
cannot be diffed, cannot travel with a pull request, and cannot be pointed at when an
implementation drifts. It also cannot be checked: "that button is the wrong green" is an
opinion until something in the repository says which green.

The second is that designing the screens surfaced structural decisions the backlog had
not made, and made two of its assumptions visibly wrong. Those are not style questions —
they change which feature owns which screen, and they will be re-litigated every time
someone builds a piece of the UI unless they are written down.

An earlier draft of the design lived in `frontend/` as stubbed screens, on the argument
that "at least it exists". That was rejected: the artboard markup is inline-styled, uses
literal hex values and carries no state layer, so it violates three rules of the
`frontend` conventions on arrival. Merged into `frontend/`, it would be indistinguishable
in git history from real code within weeks, and every later feature would either inherit
the debt or pay to remove it — while the work of turning it into real components (tokens,
primitives, a route table) is exactly what F9.6 and F9.4 exist to do deliberately.

## Decision

### The reference lives in `docs/design/` and outranks the code

`docs/design/` holds one plain HTML file per screen, a `design.css` that defines every
colour, radius and control measurement once, and `components.md` giving each primitive's
anatomy in numbers. No build step and no dependencies: the files open in a browser and
link to each other, so the designed product can be clicked through.

It carries the same contract `docs/architecture/` already has. When the built UI and the
reference disagree, the built UI is wrong. When implementation shows the design itself is
wrong, `docs/design/` is changed **in the same commit** as the code — never as a later
cleanup pass. A reference that is out of date is a defect, not technical debt.

`design.css` is what makes this enforceable rather than aspirational: screens reference
token names, never literals, so a divergence is a named difference instead of an argument
about shades. When F9.6.1 lands, its values move into
`frontend/src/shared/styles/colors.css` as a Tailwind `@theme` layer and are checked
against this file.

### The visual language is ported, not invented

Colour tokens, the 12px/16px radii and the control anatomy are taken unchanged from the
sibling project budget-checker, which F9.2.3 and F9.6.1 already name as the source. The
two projects stay recognisably related, and F9.6.1 remains a port rather than a redesign.

### `/` is one route with two states

The backlog had authentication landing nowhere: F6.7's dashboard is the only landing view
and sits six epics away from login. Rather than invent a second route, `/` renders an
empty state — account facts, an honest "no receipts yet", one way forward — which F6.7
later replaces with the dashboard at the same address. `home.html` and `dashboard.html`
are the same route at two milestones.

### Ingestion is one flow in three steps

Reading a receipt and reconciling overlapping photos happen **while a receipt is being
taken in**, not in a section the user visits. The upload wizard is therefore
photos → what we read → resolve.

The three steps stay in the epics whose endpoints they exercise: F2.6 builds step 1 and
the stepper frame, F3.7 supplies step 2 over E3's extraction, F4.7 supplies step 3 over
E4's matching. What changed is their framing — both were written as standalone
destinations ("Receipt review and correction interface", "Match review interface") and are
now named as the steps they are, with a dependency on F2.6.

> **Amended.** An earlier revision of this ADR said F3.7 and F4.7 should *become tasks
> under F2.6*. That was wrong: it would have made F2.6 unfinishable until E3 and E4 both
> landed, breaking the vertical slice in the other direction. Only the framing was at
> fault, not the placement.

"Receipts" in the navigation means the list of stored receipts, with a detail dialog —
the read side of F3.5's persistence, now F3.8. Pointing that navigation entry at a receipt
review screen, as the first draft did, is what made ingestion-time conflicts appear in the
wrong place.

### One conflict queue, blocking until empty

Everything needing a human decision queues together on step 3, whatever its kind: an item
caught in two overlapping frames (B2–B4), a field read below the confidence threshold
(A10), a receipt matching one already stored (A14), a missing total (A11). One counter,
and nothing is written while anything is open — a merge conflict list, not a wizard that
shrugs and moves on. Decisions the agent made on its own appear in the same queue, marked
settled and reversible, so automatic behaviour is visible rather than hidden.

### Authentication uses routes, not a modal

budget-checker signs in through a tabbed modal. This product uses separate `/login` and
`/register` routes, because F1.5 requires a public-versus-authenticated route table with
a redirect on expiry, and a modal has no route to redirect to.

## Consequences

- The backlog changes that follow have landed: F3.7 and F4.7 renamed as wizard steps and
  made to depend on F2.6, F3.8 added for the receipt list and detail, F9.4 groomed with a
  public landing screen, and F1.5 retired into F1.1.6/F1.1.7/F1.2.5/F1.2.6 beside the
  endpoints they exercise.
- Building a screen starts by opening its file in `docs/design/`. The `frontend` skill and
  the local `CLAUDE.md`/`AGENTS.md` point there — but both of those are untracked in this
  repository, so `docs/README.md` and this ADR are the discoverable path for anyone else.
- The reference will rot if the same-commit rule is not kept. That is the cost accepted in
  exchange for a design that can be diffed, reviewed and pointed at.
- Nothing here constrains the component API. Whether `Button` takes `variant` or
  `intent`, and what its props are called, is F9.6.3's decision to make with real code in
  hand; `components.md` describes roles and measurements, deliberately not signatures.
