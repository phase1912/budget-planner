# Reading evaluation set (F15.5.4)

`receipts/` holds one folder per receipt — its photos (`1.jpg`, `2.jpg`, …) and an
`expected.json` with the right `receipt_total` and every `line_items` entry's `name` and
`total_price`, discounts, deposits and rounding included. It is never committed: these
are people's receipts, and only those whose owners agreed to share them go in.

Score the configured model (`LLM_MODEL`) before and after a change to reading:

    docker exec -w /app budget-planner-backend-1 .venv/bin/python scripts/evaluate_reading.py evaluation/receipts
