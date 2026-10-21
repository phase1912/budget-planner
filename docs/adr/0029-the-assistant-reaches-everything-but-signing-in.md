# ADR 0029: The assistant reaches everything but signing in

**Date:** 2026-10-21
**Status:** Proposed — F21.10, F21.11, F21.12; amends ADR-0025

## Context

ADR-0025 gave settings and the account no tool, so the assistant could not touch what
it should not. In use, this made the assistant feel half-built. "Switch to Polish", "my
payday is the 10th", or an admin's "give her the paid plan until December" all send the
user back to a screen. Approved cards (ADR-0025) already make every write safe: nothing
is saved until the user sees it and approves it.

One gap is different: what guards signing in. A chat message is not proof of who is
typing, whether on a borrowed phone or in a session left open. Changing the password,
the email or the second factor, or deleting the account, must need the proof the screens
ask for.

## Decision

- **Everything the screens change has a tool**, behind an approved card like every other
  write:
  - balances (F21.10);
  - receipts (F21.6);
  - settings and the family (F21.11);
  - for admins, the admin console's actions (F21.12).
- **Signing in has none.** No tool exists for the password, the email, the second factor
  or deleting the account. The assistant answers a request for them with a link to the
  screen. A test holds this.
- **Reads go with every intent.** A request to change something may first look at what
  is there, such as a balance or a setting. A read only ever returns the caller's data
  (N2).
- **Admin tools follow the admin session.** They are offered only to an admin signed in
  with the second factor; super-admin tools are offered only to super admins. Every
  action goes into the admin log, as from the console. No admin tool returns another
  user's receipts, incomes or balances (N2).

## Consequences

- The assistant can be described as a tool server over the whole app. The same registry
  could later be exposed as a real MCP server.
- The set of tools grows with every screen. Each new screen action now needs its tool and
  card words, or the assistant says it cannot.
- Losing access to an open session lets an intruder change settings through cards, as
  they could on the Settings screen. It never lets them lock the owner out.
