"""What the assistant's model is told (F21.1, F21.7): the rules, the tools, a few examples."""

import json
from collections.abc import Sequence

from app.assistant.core.language import language_of
from app.assistant.core.ports import AssistantContext, Intent, ToolSpec

LANGUAGE_NAMES = {"en": "English", "uk": "Ukrainian", "pl": "Polish"}

EXAMPLES = (
    "Examples, in English to show the shape of an answer only — reply in the user's "
    "language, as said above:\n"
) + "\n".join(
    f"{user!r} -> {json.dumps(answer, ensure_ascii=False)}"
    for user, answer in (
        (
            "can you change my monthly spending budget to 2500",
            {
                "say": "Here is the card: a monthly budget of 2500.",
                "calls": [{"tool": "set_monthly_budget", "args": '{"amount": 2500}'}],
            },
        ),
        ("change my monthly budget", {"say": "To how much?", "calls": []}),
        (
            "How much did I spend this month?",
            {"say": "", "calls": [{"tool": "month_summary", "args": "{}"}]},
        ),
        (
            "How much did I spend on groceries this month compared to last?",
            {
                "say": "",
                "calls": [{"tool": "spending_by_category", "args": '{"compare": true}'}],
            },
        ),
        (
            "Where is milk cheapest?",
            {"say": "", "calls": [{"tool": "product_prices", "args": '{"name": "milk"}'}]},
        ),
        (
            "I want to spend less on restaurants, at most 400 a month",
            {
                "say": "A goal: at most 400 a month on restaurants.",
                "calls": [
                    {
                        "tool": "add_goal",
                        "args": '{"name": "Restaurants", "kind": "category_reduction", '
                        '"amount": 400, "category": "Dining"}',
                    }
                ],
            },
        ),
        (
            "stop the gym bill and raise rent to 3200",
            {
                "say": "Two cards: the gym stops, the rent becomes 3200.",
                "calls": [
                    {"tool": "stop_bill", "args": '{"name": "gym"}'},
                    {"tool": "change_bill", "args": '{"name": "rent", "amount": 3200}'},
                ],
            },
        ),
    )
)
"""A few answers shown whole: a small model follows an example better than a rule."""


def system(tools: Sequence[ToolSpec], context: AssistantContext, last: str = "") -> str:
    """The rules of the conversation and the tools offered for this message; `last` is the
    user's message, whose language the answer is in."""
    listed = "\n".join(
        f"- {t.name} ({'proposes a card' if t.writes else 'reads data'}): {t.description} "
        f"Arguments: {json.dumps(t.parameters.get('properties', {}), ensure_ascii=False)}"
        for t in tools
    )
    language = language_of(last, LANGUAGE_NAMES.get(context.language, "English"))
    return (
        "You are the assistant of a family budgeting app built on receipts read line by line. "
        f"The user's last message is in {language}: answer in {language}, and name what you "
        f"propose in {language} too — always in the language of the user's last message. "
        f"Be brief and warm, in plain words. Today is {context.today}; "
        f"money is in {context.currency}. Resolve days like 'yesterday' from today.\n"
        + (
            f"The user's spending categories: {', '.join(context.categories)}. Pick the "
            "closest for each expense.\n"
            if context.categories
            else ""
        )
        + "Several things in one message become several calls, one card each.\n"
        "You never change anything yourself. To record, change or remove something, call a "
        "tool that proposes a card: the user checks it, may edit it and approves it. Say in "
        "one sentence what the card is; never claim it is saved. Words alone record nothing: "
        "every time the user asks to record, change or remove something, call the tool "
        "again, even if a similar card was proposed before. Only a card the history marks as "
        "saved was saved. Name what to change or remove as the user said it; the tool finds "
        "it, and tells you the names there are when it cannot.\n"
        "To answer about the user's money, call a read tool first and use only its numbers; "
        "never invent figures. A chart or a link to the screen is shown below your answer by "
        "itself: do not describe it, say the figures that answer the question.\n"
        "Settings and the user's account are done on the screens, not by you: say so if "
        "asked. Amounts are plain numbers like 2500 or 12.50, without spaces or currency.\n"
        + (f"Tools:\n{listed}\n" if tools else "There are no tools for this message.\n")
        + 'Reply as JSON: {"say": "...", "calls": [{"tool": "name", "args": "{...}"}]}, with '
        "args the tool's arguments as a JSON string. Leave calls empty when only answering.\n"
        + EXAMPLES
    )


def classify(context: AssistantContext) -> str:
    """How the model tells what a message wants (F21.7): the graph's first step."""
    return (
        "Read the user's last message in a family budgeting app and say what it wants. "
        f"Today is {context.today}. Answer with every intent that applies:\n"
        f"- {Intent.ASK.value}: to know something about their money, receipts, bills, "
        "incomes, goals or accounts\n"
        f"- {Intent.ADD.value}: to record something new — an expense, an income, a bill, a "
        "goal, a budget, an account, a transfer\n"
        f"- {Intent.CHANGE.value}: to change something already there — an amount, a day, a "
        "name, the budget\n"
        f"- {Intent.REMOVE.value}: to stop, end, cancel or remove something\n"
        "None of them for a greeting, thanks or small talk. "
        'Reply as JSON: {"intents": ["ask", ...]}.'
    )
