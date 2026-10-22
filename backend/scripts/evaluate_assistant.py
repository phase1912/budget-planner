#!/usr/bin/env python
"""Score the assistant on dialogs with known answers (F21.13.4).

A user is seeded the way people use the app — a purchase card, a second card and savings,
rent and a gym bill, a salary, a holiday goal, a monthly budget — and each dialog is talked
through the real conversation service, graph and tools against the configured model (or
`--model`). The last turn is scored against what the dialog expects:

    {"cards": [{"kind": "balance", "fields": {"account_id": "Моя картка", "way": "correct"}}]}
    {"ask": ["Моя картка", "Revolut"]}   a question offering at least these, and no card
    {"says": ["16900"]}                   an answer holding these, and no card

Ids on a card are read back as the names of what they point at, amounts as numbers. Every
dialog runs in a transaction rolled back at its end, so nothing it writes is kept.

Usage (in the backend container, or with the same environment):
    python scripts/evaluate_assistant.py evaluation/assistant/dialogs.json
    python scripts/evaluate_assistant.py evaluation/assistant/dialogs.json \
        --model vertex_ai/gemini-3.6-flash --location global
"""

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EMAIL = "assistant-evaluation@example.com"


@dataclass
class Result:
    """One dialog's outcome."""

    dialog: str
    passed: bool
    why: str
    seconds: float
    calls: int
    tokens: int
    reply: str = ""
    cards: list[dict[str, Any]] = field(default_factory=list)


def _same(want: Any, got: Any) -> bool:
    """Equal as numbers when both are, else as text ignoring case."""
    try:
        return Decimal(str(want)) == Decimal(str(got))
    except (InvalidOperation, ValueError):
        return str(want).strip().lower() == str(got).strip().lower()


def _fits(want: dict[str, Any], card: dict[str, Any]) -> bool:
    fields = card.get("fields", {})
    return card.get("kind") == want["kind"] and all(
        _same(value, fields.get(name)) for name, value in want.get("fields", {}).items()
    )


def _plain(text: str) -> str:
    """Text with the spaces and separators people put in numbers taken out."""
    return re.sub(r"(?<=\d)[\s\u00a0\u202f.,](?=\d{3}\b)", "", text).lower()


def score(expect: dict[str, Any], reply: str, cards: list[dict[str, Any]]) -> tuple[bool, str]:
    """Whether the last turn's reply and cards are what the dialog expects, and why not."""
    writes = [c for c in cards if c.get("kind") not in ("answer", "choice", "attachment")]
    if "cards" in expect:
        left = list(writes)
        for want in expect["cards"]:
            match = next((c for c in left if _fits(want, c)), None)
            if match is None:
                return False, f"no {want['kind']} card like {want.get('fields')}"
            left.remove(match)
        return (not left, f"extra cards {[c['kind'] for c in left]}" if left else "")
    if writes:
        return False, f"proposed {[c['kind'] for c in writes]} instead"
    if "ask" in expect:
        choice = next((c for c in cards if c.get("kind") == "choice"), None)
        offered = " ".join(choice["fields"].get("options", [])) if choice else ""
        if choice is None and "?" not in reply:
            return False, "did not ask"
        missing = [o for o in expect["ask"] if o.lower() not in (offered + " " + reply).lower()]
        return (not missing, f"did not offer {missing}" if missing else "")
    missing = [s for s in expect["says"] if _plain(s) not in _plain(reply)]
    return (not missing, f"did not say {missing}" if missing else "")


async def _seed(session: Any, mapper: Any) -> tuple[Any, dict[str, str]]:
    """The evaluation user and their things; returns the user and each thing's name by id."""
    from datetime import UTC, datetime
    from decimal import Decimal

    from app.assistant.core.ports import ToolCall
    from app.assistant.tools.toolbox import Toolbox
    from app.core.context import current_user_id
    from app.domain.accounts import AccountKind
    from app.models.user import User
    from app.services.money_accounts import AccountService

    user = User(
        email=EMAIL,
        first_name="Eval",
        last_name="User",
        password_hash="-",
        currency="PLN",
        language="uk",
        role="admin",
        budget_limit=Decimal("3000.00"),
        email_confirmed_at=datetime.now(UTC),
    )
    session.add(user)
    await session.flush()
    current_user_id.set(user.id)
    today = datetime.now(UTC).date()
    accounts = AccountService(session)
    for name, kind, balance, purchases in (
        ("Моя картка", AccountKind.PERSONAL, "4100", True),
        ("Revolut", AccountKind.PERSONAL, "800", False),
        ("Скарбничка", AccountKind.DEPOSIT, "12000", False),
    ):
        await accounts.create(
            name=name,
            kind=kind,
            opening=Decimal(balance),
            opening_on=today,
            tax_rate=None,
            shared=False,
            for_purchases=purchases,
        )
    toolbox = Toolbox(session, user, today, goal_mapper=mapper)
    for call in (
        ToolCall("add_bill", {"name": "Оренда", "amount": "2800", "day": 1}),
        ToolCall("add_bill", {"name": "Спортзал", "amount": "120", "day": 5}),
        ToolCall("add_regular_income", {"name": "Зарплата", "amount": "9000", "day": 10}),
        ToolCall("add_goal", {"name": "Відпустка", "kind": "savings_target", "amount": "5000"}),
    ):
        card = await toolbox.propose(call)
        assert card is not None, call
        await toolbox.save(card)
    await _family_and_shopping(session, user, today)
    return user, await _names(session, user, today)


async def _family_and_shopping(session: Any, user: Any, today: Any) -> None:
    """Some shopping of the user's, read into products, and a wife in the family with
    shopping of her own."""
    from datetime import UTC, datetime
    from decimal import Decimal

    from app.core.context import current_user_id
    from app.models.user import User
    from app.repository.category import CategoryRepository
    from app.repository.household import HouseholdRepository
    from app.services.household import HouseholdService
    from app.services.manual_expense import ManualExpense, record_expense
    from app.services.product import ProductService

    categories = {c.name: c.id for c in await CategoryRepository(session).list_available(user.id)}

    async def spend(who: Any, what: str, amount: str, category: str) -> None:
        await record_expense(
            session,
            who,
            ManualExpense(what, today, Decimal(amount), None, categories[category]),
            None,
        )

    for what, amount, category in (
        ("Mleko Łaciate 3,2% 1l", "4.29", "Groceries"),
        ("Chleb żytni", "6.50", "Groceries"),
        ("Chipsy Lay's solone", "7.99", "Groceries"),
        ("Coca-Cola 1l", "6.49", "Groceries"),
        ("Pizza Margherita", "39.00", "Dining"),
    ):
        await spend(user, what, amount, category)
    await ProductService(session).link_unmatched(user.id)

    wife = User(
        email="assistant-evaluation-wife@example.com",
        first_name="Олена",
        last_name="User",
        password_hash="-",
        currency="PLN",
        language="uk",
        email_confirmed_at=datetime.now(UTC),
    )
    session.add(wife)
    await session.flush()
    households = HouseholdService(HouseholdRepository(session))
    family = await households.create(user, "Родина")
    await households.join(wife, family.invite_code)
    # Her receipts are hers: written as her, as the ownership guard insists (N2).
    current_user_id.set(wife.id)
    for what, amount, category in (
        ("Kawa latte", "16.00", "Dining"),
        ("Sushi", "120.00", "Dining"),
        ("Bilet do kina", "32.00", "Entertainment"),
    ):
        await spend(wife, what, amount, category)
    current_user_id.set(user.id)


async def _upload(session: Any, user: Any, count: int) -> tuple[Any, int] | None:
    """A reading started for `count` attached files, as the upload would start it."""
    if not count:
        return None
    from app.models.receipt import ReceiptChannel
    from app.models.upload_job import UploadJob

    job = UploadJob(user_id=user.id, total_items=count, channel=ReceiptChannel.PHOTO)
    session.add(job)
    await session.flush()
    return job.id, count


async def _names(session: Any, user: Any, today: Any) -> dict[str, str]:
    from app.repository.category import CategoryRepository
    from app.repository.goal import GoalRepository
    from app.services.income import IncomeService
    from app.services.money_accounts import AccountService

    names = {
        str(v.account.id): v.account.name
        for v in (await AccountService(session).overview(today)).accounts
    }
    incomes = IncomeService(session)
    names |= {str(b.id): b.name for b in await incomes.regular_bills()}
    names |= {str(s.id): s.name for s in await incomes.regular_incomes()}
    names |= {str(g.id): g.name for g in await GoalRepository(session).list_mine()}
    names |= {str(c.id): c.name for c in await CategoryRepository(session).list_available(user.id)}
    return names


def _named(card: dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    fields = {k: names.get(str(v), v) for k, v in (card.get("fields") or {}).items()}
    return {"kind": card.get("kind"), "fields": fields}


async def run(dialog: dict[str, Any], agent: Any) -> Result:
    """Talk one dialog through the service and score its last turn; nothing is kept."""
    from datetime import UTC, datetime

    import litellm

    from app.adapters.goal_mapping_agent import GoalMappingAdapter
    from app.assistant.core.graph import AssistantGraph
    from app.assistant.service import AssistantService
    from app.core.config import get_settings
    from app.db.session import get_session_factory
    from app.services.quota import QuotaService

    usage: list[int] = []
    original = litellm.acompletion

    async def counted(**kwargs: Any) -> Any:
        response = await original(**kwargs)
        usage.append(response.usage.total_tokens)
        return response

    litellm.acompletion = counted
    started = time.monotonic()
    try:
        async with get_session_factory()() as session:
            try:
                mapper = GoalMappingAdapter(agent)
                user, names = await _seed(session, mapper)
                service = AssistantService(
                    session,
                    AssistantGraph(agent),
                    QuotaService(session, get_settings()),
                    goal_mapper=mapper,
                )
                conversation_id = None
                seen = 0
                for said in dialog["turns"]:
                    conversation = await service.send(
                        user,
                        conversation_id,
                        said,
                        datetime.now(UTC).date(),
                        attachment=await _upload(session, user, dialog.get("attached", 0)),
                    )
                    conversation_id = conversation.id
                    fresh = conversation.messages[seen:]
                    seen = len(conversation.messages)
                reply = " ".join(m.text for m in fresh if m.role == "assistant" and m.text)
                cards = [_named(m.card, names) for m in fresh if m.card]
            finally:
                await session.rollback()
    finally:
        litellm.acompletion = original
    passed, why = score(dialog["expect"], reply, cards)
    return Result(
        dialog["id"], passed, why, time.monotonic() - started, len(usage), sum(usage), reply, cards
    )


async def main(path: Path, model: str | None, location: str | None, verbose: bool) -> None:
    import app.main  # noqa: F401 — loads the app's modules in the order the app does
    from app.agent.core import Agent
    from app.agent.factory import agent_from_settings
    from app.core.config import get_settings

    settings = get_settings()
    agent = (
        Agent(
            model=model,
            vertex_project=settings.vertex_project,
            vertex_location=location or settings.vertex_location,
        )
        if model
        else agent_from_settings()
    )
    results = []
    for dialog in json.loads(path.read_text()):
        try:
            result = await run(dialog, agent)
        except Exception as exc:
            result = Result(dialog["id"], False, f"failed: {exc}", 0, 0, 0)
        results.append(result)
        mark = "pass" if result.passed else "FAIL"
        print(
            f"{mark}  {result.dialog:40} {result.seconds:5.1f}s {result.calls:2} calls "
            f"{result.tokens:6} tok  {result.why}"
        )
        if verbose and not result.passed:
            print(f"      reply: {result.reply[:200]!r}\n      cards: {result.cards}")
    passed = sum(r.passed for r in results)
    print(
        f"\n{agent.model}: {passed}/{len(results)} passed · "
        f"{sum(r.seconds for r in results) / max(len(results), 1):.1f}s and "
        f"{sum(r.tokens for r in results) // max(len(results), 1)} tokens a dialog"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("dialogs", type=Path)
    parser.add_argument("--model", help="a LiteLLM model instead of LLM_MODEL")
    parser.add_argument("--location", help="the Vertex location for --model, e.g. global")
    parser.add_argument("-v", "--verbose", action="store_true", help="show failed replies")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.dialogs, arguments.model, arguments.location, arguments.verbose))
