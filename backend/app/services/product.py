import uuid
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import NotFoundError
from app.domain.products import ProductKey, abbreviates, candidates, product_key
from app.models.product import Product, ProductAlias
from app.ports.product_matching import MatchQuestion, ProductMatcherPort
from app.repository.product import ProductRepository

QUESTIONS_PER_CALL = 40
"""How many ambiguous names one model call is asked about."""


@dataclass(frozen=True)
class Variant:
    """One way a product is printed, and how often it was bought under it."""

    alias_id: uuid.UUID
    printed_name: str
    purchases: int


@dataclass(frozen=True)
class ProductSummary:
    """A product as the products list shows it (F16.1)."""

    id: uuid.UUID
    name: str
    size_amount: Decimal | None
    size_unit: str | None
    purchases: int
    shops: int
    last_bought: datetime | None
    spent: Decimal
    variants: list[Variant]


class ProductService:
    """The user's products: matching printed lines to them, merging and splitting (F16.1)."""

    def __init__(self, session: AsyncSession, matcher: ProductMatcherPort | None = None) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.matcher = matcher

    async def link_unmatched(self, user_id: uuid.UUID) -> int:
        """Match every line of the user's with no product yet; returns how many were matched.

        A known way of printing goes to its product; a name abbreviating a known one, of
        the same size, joins it and becomes a known way too; a name only like some is put
        to the model, and with no answer, or nothing like it, starts a product of its own.
        Commonest names go first, so a product is named the way it is usually printed.
        """
        lines = await self.products.unmatched_lines(user_id)
        if not lines:
            return 0
        by_key: dict[str, list[uuid.UUID]] = defaultdict(list)
        printed: dict[str, Counter[str]] = defaultdict(Counter)
        keys: dict[str, ProductKey] = {}
        for line_id, name in lines:
            key = product_key(name)
            if not key.words:
                continue
            by_key[key.text].append(line_id)
            printed[key.text][name] += 1
            keys[key.text] = key

        aliases = await self.products.aliases(user_id)
        owner = {alias.key: alias.product_id for alias in aliases}
        known: list[tuple[ProductKey, uuid.UUID]] = [
            (product_key(a.printed_name), a.product_id) for a in aliases
        ]
        questions: list[tuple[str, list[uuid.UUID]]] = []
        for text in sorted(by_key, key=lambda t: -len(by_key[t])):
            key, name = keys[text], printed[text].most_common(1)[0][0]
            product_id = owner.get(text) or next((p for k, p in known if abbreviates(key, k)), None)
            if product_id is None and self.matcher is not None:
                offered = candidates(key, known)
                if offered:
                    questions.append((text, offered))
                    continue
            if product_id is None:
                product_id = await self._new_product(user_id, key, name)
            await self._remember(user_id, product_id, text, name, owner, known, key)
            await self.products.link(by_key[text], product_id)

        if questions and self.matcher is not None:
            await self._ask(user_id, questions, by_key, printed, keys, owner, known)
        await self.session.flush()
        return sum(len(ids) for text, ids in by_key.items() if text in owner)

    async def _ask(
        self,
        user_id: uuid.UUID,
        questions: list[tuple[str, list[uuid.UUID]]],
        by_key: dict[str, list[uuid.UUID]],
        printed: dict[str, Counter[str]],
        keys: dict[str, ProductKey],
        owner: dict[str, uuid.UUID],
        known: list[tuple[ProductKey, uuid.UUID]],
    ) -> None:
        assert self.matcher is not None
        # Every way a candidate is printed is evidence: its shown name alone may not be.
        names = {
            p.id: " / ".join(dict.fromkeys([p.name, *(a.printed_name for a in p.aliases)]))
            for p in await self.products.list_with_aliases(user_id)
        }
        for start in range(0, len(questions), QUESTIONS_PER_CALL):
            batch = questions[start : start + QUESTIONS_PER_CALL]
            asked = [
                MatchQuestion(
                    printed[text].most_common(1)[0][0],
                    {str(i + 1): names[p] for i, p in enumerate(offered) if p in names},
                )
                for text, offered in batch
            ]
            answers = await self.matcher.match(asked)
            for (text, offered), question in zip(batch, asked, strict=True):
                ref = answers.get(question.name)
                chosen = int(ref) if ref and ref.isdigit() else 0
                product_id = (
                    offered[chosen - 1]
                    if 1 <= chosen <= len(offered)
                    else await self._new_product(user_id, keys[text], question.name)
                )
                await self._remember(
                    user_id, product_id, text, question.name, owner, known, keys[text]
                )
                await self.products.link(by_key[text], product_id)

    async def _new_product(self, user_id: uuid.UUID, key: ProductKey, name: str) -> uuid.UUID:
        product = Product(
            user_id=user_id,
            name=name.strip(),
            size_amount=key.size.amount if key.size else None,
            size_unit=key.size.unit if key.size else None,
        )
        self.session.add(product)
        await self.session.flush()
        return product.id

    async def _remember(
        self,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        text: str,
        name: str,
        owner: dict[str, uuid.UUID],
        known: list[tuple[ProductKey, uuid.UUID]],
        key: ProductKey,
    ) -> None:
        if text in owner:
            return
        self.session.add(
            ProductAlias(user_id=user_id, product_id=product_id, key=text, printed_name=name)
        )
        owner[text] = product_id
        known.append((key, product_id))

    async def list_products(self, user_id: uuid.UUID, search: str = "") -> list[ProductSummary]:
        """The user's products, most bought first, with how each is printed (F16.1).

        `search` keeps the products whose name or any printed variant contains it,
        ignoring case and diacritics. Lines not matched yet are matched first.
        """
        await self.link_unmatched(user_id)
        products = await self.products.list_with_aliases(user_id)
        stats = await self.products.purchases(user_id)
        lines = await self.products.lines_of(user_id, [p.id for p in products])
        per_alias: Counter[tuple[uuid.UUID, str]] = Counter(
            (product_id, product_key(name).text) for _, product_id, name in lines
        )
        wanted = " ".join(product_key(search).words) if search.strip() else ""
        summaries = []
        for product in products:
            names = [product.name, *(a.printed_name for a in product.aliases)]
            if wanted and not any(wanted in " ".join(product_key(n).words) for n in names):
                continue
            times, shops, last, spent = stats.get(product.id, (0, 0, None, Decimal(0)))
            summaries.append(
                ProductSummary(
                    id=product.id,
                    name=product.name,
                    size_amount=product.size_amount,
                    size_unit=product.size_unit,
                    purchases=times,
                    shops=shops,
                    last_bought=last,
                    spent=spent,
                    variants=sorted(
                        (
                            Variant(a.id, a.printed_name, per_alias[(product.id, a.key)])
                            for a in product.aliases
                        ),
                        key=lambda v: (-v.purchases, v.printed_name),
                    ),
                )
            )
        return sorted(summaries, key=lambda s: (-s.purchases, s.name.lower()))

    async def merge(
        self, user_id: uuid.UUID, target_id: uuid.UUID, source_ids: Sequence[uuid.UUID]
    ) -> None:
        """Make other products part of `target_id`: their lines and ways of printing (F16.1).

        The target keeps its name; the others are gone. Raises NotFoundError when any
        product is not the user's (N2).
        """
        target = await self.products.get(user_id, target_id)
        sources = [await self.products.get(user_id, s) for s in source_ids if s != target_id]
        if target is None or any(s is None for s in sources):
            raise NotFoundError("Product not found")
        for source in sources:
            assert source is not None
            moved = [
                line_id for line_id, _, _ in await self.products.lines_of(user_id, [source.id])
            ]
            await self.products.link(moved, target.id)
            for alias in list(source.aliases):
                alias.product = target  # moved, not orphaned: deleting the source keeps it
            await self.session.flush()
            await self.session.delete(source)
        await self.session.flush()

    async def split(self, user_id: uuid.UUID, product_id: uuid.UUID, alias_id: uuid.UUID) -> None:
        """Take one way of printing out of a product into a product of its own (F16.1).

        Its lines go with it, and so do later ones printed the same way. Raises
        NotFoundError for a product or variant that is not the user's (N2), and
        ValueError when it is the product's only variant: there is nothing to split from.
        """
        product = await self.products.get(user_id, product_id)
        alias = next((a for a in product.aliases if a.id == alias_id), None) if product else None
        if product is None or alias is None:
            raise NotFoundError("Product not found")
        if len(product.aliases) < 2:
            raise ValueError("A product printed one way only cannot be split")
        new_id = await self._new_product(
            user_id, product_key(alias.printed_name), alias.printed_name
        )
        moved = [
            line_id
            for line_id, _, name in await self.products.lines_of(user_id, [product.id])
            if product_key(name).text == alias.key
        ]
        alias.product_id = new_id
        await self.products.link(moved, new_id)
        await self.session.flush()
