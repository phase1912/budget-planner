# ADR 0028: The assistant as a module of its own, on LangGraph

**Date:** 2026-10-21
**Status:** Accepted — F21.7; builds on ADR-0025. The classify node is superseded by
ADR-0032: every tool is offered, in a loop of the provider's own tool calling.

## Context

The assistant began as one loop over a few tools: read the month, propose a budget, an
income, a bill or an expense. Its code was spread across six files in four layers: an
adapter, a port, two services, a schema and a router. F21.7 asks for every thing the user
keeps — incomes, bills, the budget, goals, accounts and transfers — to be added, changed
and removed in words. Later work adds receipts reviewed and edited from the chat and the
state of what waits for review. Offered every tool at once, a small model picks wrongly
more often as the list grows, and each new tool had to be wired into dispatch code by hand.

## Decision

- **A module, not layers.** Everything of the assistant lives in `app/assistant/`: `core`
  (the agent), `tools`, `service` and `api`. The core imports neither the database nor
  FastAPI, and a test holds that, so the agent can be tested, and one day moved out as a
  package, alone. A separate installable package was weighed and left for later: it would
  change the build and CI before giving anything the folder does not.
- **An agent graph, LangGraph.** The graph's first node classifies what the message wants:
  to ask, to add, to change or to remove. The model is then offered only the tools serving
  those wishes. A failed classification offers every tool, so a guess never withholds what
  the user needed. LangGraph (MIT, open source) was chosen over hand-written branching for
  its explicit nodes and edges, which later branches (review a receipt, confirm several
  cards) extend without rewriting the loop.
- **A tool is a class.** `Reader` or `Writer`, with its arguments, its intents and, for a
  writer, the card it proposes and how it saves it. Defining it registers it: no dispatch,
  prompt or client change is needed. A writer finds what to change by the name the user
  said, and refuses with the names there are when it cannot, for the model to try again.
- **Cards drawn from a form.** The commonest cards (budget, income, bill, expense) keep
  their own design. Any other kind is drawn by the client from the fields the writer
  declares (`target`, `amount`, `repeat`, `category`, `account`, `choice`…), so a new kind
  of action needs only words for its title and fields.

ADR-0025 stands unchanged: nothing is written until the user approves a card, through the
same service as the screens, and settings and the account have no tool.

## Consequences

- Each message costs one more small model call, the classification: a few hundred tokens.
- A removal through the assistant does what the screen does. A rule stops from next month,
  this month's income can go, and the last card removed goes back to a budget alone.
- New abilities — showing and correcting a receipt, the state of what waits for review —
  are new tool modules, and new graph branches only where a flow needs more than one step.
