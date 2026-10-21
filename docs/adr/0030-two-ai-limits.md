# ADR 0030: Two AI limits — receipts, and everything else the user asks of the model

**Date:** 2026-10-21
**Status:** Proposed — F21.9

## Context

Today one monthly quota counts receipt reads: 10 free, 200 paid (F10.6, F18.2). Every 10
assistant messages cost one read. Goal mapping and advice on a goal are model calls that
count nowhere; only a per-IP rate limit holds them back. The earlier plan was one AI
budget charged by tokens. With 10 free reads, though, a few conversations would leave no
receipts to read, and receipts are what the product is for.

## Decision

- **Two monthly limits.**
  - Receipt reads stay as they are, counted per receipt.
  - A separate **AI allowance**, counted in tokens, covers every other model call the
    user starts:
    - assistant messages;
    - mapping a lifestyle goal when it is stated or reworded;
    - advice asked for on a goal;
    - reading an income document.
- **What runs unasked is the service's cost.** This covers proactive advice on goals at
  risk, categorising a read receipt and matching products. These calls are recorded but
  charged to no one's allowance.
- **Every call is recorded in one place in the agent**, with its purpose and its tokens
  in and out, so a new caller cannot skip the count. The allowance is checked before the
  call.
- The service-wide daily ceiling covers both limits. Admins are exempt from both.
- Each plan's allowance is set in configuration. The numbers are fixed once costs are
  measured (F18.2.1).

## Consequences

- Talking to the assistant never costs a receipt read; `assistant_messages_per_read` is
  retired.
- Goals now cost the user something. Spending the allowance shows a calm "used up" state
  with the reset date, and typing by hand stays free.
- The user sees two meters instead of one.
