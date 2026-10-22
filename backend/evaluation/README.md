# Reading evaluation set (F15.5.4)

`receipts/` holds one folder per receipt — its photos (`1.jpg`, `2.jpg`, …) and an
`expected.json` with the right `receipt_total` and every `line_items` entry's `name` and
`total_price`, discounts, deposits and rounding included. It is never committed: these
are people's receipts, and only those whose owners agreed to share them go in.

Score the configured model (`LLM_MODEL`) before and after a change to reading:

    docker exec -w /app budget-planner-backend-1 .venv/bin/python scripts/evaluate_reading.py evaluation/receipts

# Assistant evaluation set (F21.13.4)

`assistant/dialogs.json` is about forty dialogs in Ukrainian, Polish, English and Russian
with what each must end in: a card of a kind with some of its fields, a question offering
at least some options, or an answer holding some words. A user is seeded the way people use
the app: three cards (one paying for purchases), rent and a gym bill, a salary, a holiday
goal, a budget, some shopping read into products, and a wife in the family with shopping
of her own. Each dialog is talked through the real service, graph and tools and rolled back.
Unlike the receipts, these are made up and committed.

Score the configured model, or another one, before and after a change to the assistant:

    PYTHONPATH=. uv run python scripts/evaluate_assistant.py evaluation/assistant/dialogs.json -v
    PYTHONPATH=. uv run python scripts/evaluate_assistant.py evaluation/assistant/dialogs.json \
        --model vertex_ai/gemini-3.6-flash --location global
