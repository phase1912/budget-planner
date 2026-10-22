# ADR 0030: One monthly wallet of AI credits, spent by what each call really costs

**Date:** 2026-10-22
**Status:** Accepted — F21.9. The first proposal on this record, two limits (receipts, and
everything else in tokens), was not taken.

## Context

Until now one monthly quota counted receipt reads: 10 free, 200 paid (F10.6, F18.2).
Every 10 assistant messages cost one read. A recording, a lifestyle goal mapped and advice
asked for counted nowhere; only per-IP rate limits held them back.

The app is presented as something the user does everything in by talking to it. Splitting
"receipts" from "AI" splits one thing: a photo attached in the chat is both.

Raw tokens are no measure either, because they do not cost the same. On Gemini 2.5 Flash:
- an output token costs eight times an input token ($2.50 against $0.30 a million);
- the model's thinking is billed as output;
- sound costs $1.00 a million tokens on the model, or $0.016 a minute on Speech-to-Text.

Measured or estimated per action:
- a receipt read with its categories: about $0.01;
- a message to the assistant: about $0.003–0.005;
- seven seconds of speech: about $0.002.

## Decision

- **One wallet, counted in money.** A credit is 0.001 USD of what the call cost. The free
  plan gets 150 credits a month and the paid plan 2 500. Admins have no limit.
- **Every call is recorded where it is made.** The agent (`Agent`, `app/agent/metering.py`)
  records each call:
  - who it was for;
  - what it was for (receipt, categories, assistant, speech, goal mapping, advice, income
    document, products);
  - the model, and tokens in and out;
  - its cost from LiteLLM's own price table, thinking included.

  Speech-to-Text records its seconds. A record is written in a session of its own, so it
  survives a request that rolls back. A job that runs after its request names its payer.
- **What nobody asked for is the service's cost.** Proactive advice, and matching products
  when the list opens, are recorded but charged to no one.
- **Checked before, spent after.** Every action is checked against what such an action has
  cost across the service in the last 30 days: per receipt, the receipt and categories
  credits over receipts read; per message, the assistant credits over messages. Until 20 of
  each were recorded, the configured 10 and 4 credits stand in. A receipt still being read
  counts at once, so a burst of uploads cannot overdraw the month. The month renews on the
  first, UTC.
- **The user sees receipts and messages, never credits.** "About 7 receipts or 17 messages
  left" appears on the Add screen, in the assistant and in Settings. A refusal says the
  same and when the credits renew. Typing by hand never costs anything.
- **One free request is bounded**, so the month cannot go at once:
  - an upload holds at most 5 receipts;
  - a message takes at most 4 rounds of tools;
  - a recording is a minute at most, by its own length, whatever the file's size.
- **The service-wide day is bounded:** 3 000 credits ($3) across non-admin accounts.

## Consequences

- At $0.01 a receipt the free month is about 15 receipts with no talk, or about 10
  receipts and a dozen messages. The paid month is about 200 receipts and 100 messages.
- Margin, for a paid plan at 19.99 zł:
  - about $3.46 reaches us after VAT and the store's 15%;
  - the paid allowance costs at most $2.50;
  - a user who spends the whole month leaves a 28% margin, just under the 30% target.
    The margin rises with every user who does not spend the month.

  The price itself is F18.2's to set.
- The figures shown follow what things really cost: a dearer model shows fewer receipts
  left without any change to the code.
- Every call writes one row. The `ai_usage` table is the bill, readable by purpose, model
  and day.
- `assistant_messages_per_read`, `monthly_receipt_quota` and `daily_receipt_read_ceiling`
  are gone. Terraform passes `FREE_MONTHLY_CREDITS`, `PAID_MONTHLY_CREDITS` and
  `DAILY_CREDIT_CEILING` instead.
