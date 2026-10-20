# ADR 0026: Reading receipts from any country

**Date:** 2026-10-20
**Status:** Accepted — F15.5

## Context

The reader's prompt and its reconciliation rules were written for Polish receipts: they
named OPUST, SUMA PLN, DO ZAPŁATY and kaucja. The first Ukrainian receipts failed on a
discount, on a rounding line and on a McDonald's menu whose priced add-on was folded into
the meal. The product is for Europe, so every new country would have repeated that, and
each fix made by hand for one receipt risked breaking another nobody re-read.

Reading also ran with the model's thinking switched off, because Gemini 2.5's thoughts
shared the answer's token limit and an unbounded one cut the JSON off.

## Decision

- **One table of conventions** (`app/domain/receipt_conventions.py`): rules every receipt
  follows (a discount is its own negative line, a footer sum of discounts or a payment is
  no line, a menu's unpriced parts are no lines but a priced add-on is), then each
  country's words for discount, deposit, rounding, totals and payments and how it marks
  VAT, then notes for chains that print their own way. The prompt is built from it and the
  reconciliation rules take their words from it. A country or a chain is added there, and
  nowhere else.
- **Thinking with a fixed budget.** The model may think up to `READING_THINKING_BUDGET`
  tokens, added on top of the answer's limit, so a thought can never cut the answer off.
- **Photos made legible first**: upright from EXIF, cropped to the receipt, grey with its
  contrast stretched, no larger than the model reads in full. Only the copy sent to the
  model is changed; the stored photo is kept as before.
- **Changes are measured.** `scripts/evaluate_reading.py` scores the configured model on
  receipts with known answers. The receipts themselves are people's data and stay out of
  git; only those their owners agreed to share are used.

## Consequences

- A new market costs one row of words, checked on a few of its receipts with the score.
- The prompt grows by a few hundred tokens with every country listed: a fraction of a
  cent per receipt. Thinking costs about as much again per receipt on Gemini 2.5 Flash.
- The words are knowledge about receipts, not law: a chain that prints differently gets a
  note when its receipts are seen to fail, and the score shows whether the note helped.
