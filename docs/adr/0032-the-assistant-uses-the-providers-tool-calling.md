# ADR 0032: The assistant uses the provider's own tool calling, and knows what the user has

**Date:** 2026-10-22
**Status:** Accepted — F21.13; supersedes ADR-0025's "provider-agnostic calling" and
ADR-0028's classify node

## Context

On 2026-10-22 the assistant was measured against the real model, tools and database:
- "update the balance on my card for expenses" asked the user to name the card, turn
  after turn;
- "on the first card" and "the one I pay for shopping with" fared no better;
- "wakacje" did not find the goal "Відпустка", nor "siłownia" the bill "Спортзал";
- "which bill?" came as a question with nothing to tap.

Neither the token limits (answers were short and none was cut off) nor LangGraph was the
cause. The causes were in how the agent was built:
- **The model did not know what the user had.** The cards it read lacked the role that
  says which pays for purchases.
- **The prompt told it to pass the user's own words**, and the tools matched names only.
- **Calls went through a JSON protocol of our own**: arguments as a string inside a
  structured answer. Models are trained for their provider's function calling instead.
- **A classifier first guessed the message's wish** and withheld the tools for the
  others, at the cost of an extra call each message.

A newer model (`gemini-3.6-flash`) on the old design understood "the first card" but not
"the card for expenses", and took three to four times as long.

## Decision

- **The provider's own tool calling, in a loop.**
  - `Agent.run_tools` offers every tool as a function through LiteLLM, which Gemini and
    OpenAI-compatible local models (LM Studio) both take.
  - The graph has two nodes. `think` calls the model. `use` runs what it asked for and
    answers each call with its result:
    - a read runs at once;
    - a write is checked and kept as a proposed card;
    - a refused write comes back with why and what there is.

    The loop runs until the model answers in words, eight rounds at most.
  - The model's turn is sent back as it came, so Gemini's thought signatures survive.
  - There is no classifier and no second look.
- **What the user has, in every turn.** The system prompt carries a summary:
  - every card numbered as the Accounts screen lists it, with kind, balance and which
    pays for purchases;
  - the budget, bills, incomes, goals, product groups and recent trips;
  - the family.

  The model resolves "the card for expenses", "the first one" or a name in another
  language itself, and passes the exact name. Finding a card also accepts its number and
  the purchase role, as a safety net.
- **A question is options to tap.** The `ask_user` tool ends the turn with a question and
  its options. A tap sends the option as the user's answer. A question that a read tool
  can answer is not asked.
- **More of the app as tools.** These are new tools:
  - products found by any spelling (receipts print them in the shop's language);
  - products saved as a group;
  - the family's spending: who spent how much and on what, a member's private receipts
    only as one sum (ADR-0017).

  Files attached in the chat go through the receipt upload and are checked on the Add
  screen (F21.8.2).
- **Measured, not felt.** `scripts/evaluate_assistant.py` scores about forty committed
  dialogs in Ukrainian, Polish, English and Russian against any model.

## Results

| Engine and model | Dialogs passed | Tokens a dialog |
|---|---|---|
| Old graph, `gemini-2.5-flash` | 15 / 30 | 9 700 |
| This design, `gemini-2.5-flash` | 29 / 30 | 6 300 |
| This design, `gemini-3.6-flash` | 28 / 30 | 10 000 |
| This design, `gemini-2.5-flash`, set grown to 37 | 37 / 37 | 7 100 |

- The run of 37 first scored 34. Two of the three misses were the set's own figures,
  which had not counted the purchases seeded on the card (the assistant's answers were
  right). The third was a question that offered the two cards but not the savings
  account, now accepted.
- Answers take two to six seconds.
- The local `qwen3.5-9b` passed four sample dialogs of four through LM Studio, so local
  work keeps the same engine.
- `gemini-2.5-flash` stays the production model: the newer one is no better here and
  costs more.

## Consequences

- Every tool, 34 of them, is in every request: a whole call, prompt and declarations
  included, measured 3 200–3 800 tokens. That is still fewer per dialog than the old
  engine spent on its classifier and second calls.
- The prompt grows with what the user has. It is kept to names and the figures a
  reference needs, and the read tools hold the rest.
- A change to the assistant is judged by the evaluation before and after, as reading is
  by `evaluate_reading.py` (F15.5.4).
