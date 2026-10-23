import uuid
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import NotFoundError
from app.core.config import get_settings
from app.domain.periods import DateRange
from app.domain.product_overview import ProductsOverview, products_overview
from app.domain.products import ProductKey, abbreviates, candidates, product_key
from app.domain.purchases import (
    CheaperShop,
    Exploration,
    PricePoint,
    ProductFacts,
    base_price,
    cheaper_elsewhere,
    explore,
)
from app.models.product import Product, ProductAlias
from app.models.selection import ProductSelection
from app.models.user import User
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
    cheaper: CheaperShop | None = None


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
        await self._rekey(user_id)
        lines = await self.products.unmatched_lines(user_id)
        if not lines:
            return 0
        # Without the owner's leave, product names never reach the model (F25.3.2).
        owner_row = await self.session.get(User, user_id)
        matcher = self.matcher if owner_row and owner_row.ai_consent_at else None
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
            if product_id is None and matcher is not None:
                offered = candidates(key, known)
                if offered:
                    questions.append((text, offered))
                    continue
            if product_id is None:
                product_id = await self._new_product(user_id, key, name)
            await self._remember(user_id, product_id, text, name, owner, known, key)
            await self.products.link(by_key[text], product_id)

        if questions and matcher is not None:
            await self._ask(user_id, questions, by_key, printed, keys, owner, known)
        await self.session.flush()
        return sum(len(ids) for text, ids in by_key.items() if text in owner)

    async def _rekey(self, user_id: uuid.UUID) -> None:
        """Bring known ways of printing up to how names are matched now (F16.1).

        When matching changes, as when billing periods stopped counting as part of a name,
        products told apart only by what no longer counts become one again: the most
        bought keeps its name and saved selections follow, as in `merge`.
        """
        aliases = list(await self.products.aliases(user_id))
        fresh = {a.id: product_key(a.printed_name).text for a in aliases}
        stale = [a for a in aliases if a.key != fresh[a.id]]
        if not stale:
            return
        groups: dict[str, list[ProductAlias]] = defaultdict(list)
        for alias in aliases:
            groups[fresh[alias.id]].append(alias)
        bought = {pid: facts[0] for pid, facts in (await self.products.purchases(user_id)).items()}
        names = {p.id: p.name for p in await self.products.list_with_aliases(user_id)}
        merged_into: dict[uuid.UUID, uuid.UUID] = {}
        kept: list[ProductAlias] = []
        for text, group in groups.items():
            if all(a.key == text for a in group):
                continue
            owners = list(dict.fromkeys(self._current(a.product_id, merged_into) for a in group))
            target = max(owners, key=lambda p: bought.get(p, 0))
            if len(owners) > 1:
                await self.merge(user_id, target, owners)
                merged_into.update({p: target for p in owners if p != target})
            keep = next(
                (a for a in group if a.key == text),
                next((a for a in group if a.printed_name == names.get(target)), group[0]),
            )
            kept.append(keep)
            for alias in group:
                if alias is not keep:
                    await self.session.delete(alias)
        # Two steps, so a key taken over from an alias that is itself changing never
        # meets it in the unique (user, key) index mid-update.
        for alias in kept:
            alias.key = f"~{alias.id}"
        await self.session.flush()
        for alias in kept:
            alias.key = fresh[alias.id]
        await self.session.flush()
        self.session.expire_all()

    @staticmethod
    def _current(product_id: uuid.UUID, merged_into: dict[uuid.UUID, uuid.UUID]) -> uuid.UUID:
        while product_id in merged_into:
            product_id = merged_into[product_id]
        return product_id

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
        cheaper = await self._cheaper_shops(user_id, products)
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
                    cheaper=cheaper.get(product.id),
                )
            )
        return sorted(summaries, key=lambda s: (-s.purchases, s.name.lower()))

    async def _cheaper_shops(
        self, user_id: uuid.UUID, products: Sequence[Product]
    ) -> dict[uuid.UUID, CheaperShop]:
        """Each product's cheaper shop, from recent counted purchases only (F16.3)."""
        facts = {p.id: ProductFacts(p.id, p.name, p.size_amount, p.size_unit) for p in products}
        points: dict[uuid.UUID, list[PricePoint]] = defaultdict(list)
        for purchase in sorted(
            await self.products.purchases_of(user_id, list(facts), None), key=lambda p: p.day
        ):
            product = facts[purchase.product_id]
            points[product.id].append(
                PricePoint(
                    purchase.day,
                    purchase.shop,
                    purchase.unit_price,
                    base_price(product, purchase.unit_price),
                )
            )
        freshness = timedelta(days=get_settings().price_freshness_days)
        today = datetime.now(UTC).date()
        found = {pid: cheaper_elsewhere(pts, today, freshness) for pid, pts in points.items()}
        return {pid: shop for pid, shop in found.items() if shop is not None}

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
        await self._follow(user_id, {str(src.id) for src in sources if src}, [str(target.id)])
        await self.session.flush()

    async def rename(self, user_id: uuid.UUID, product_id: uuid.UUID, name: str) -> None:
        """Show a product under a name of the user's choosing (F16.1).

        Only the shown name changes: matching goes by how receipts print it (the aliases),
        so later receipts still find the product. Raises NotFoundError for a product that
        is not the user's (N2).
        """
        product = await self.products.get(user_id, product_id)
        if product is None:
            raise NotFoundError("Product not found")
        product.name = name
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
        # The user picked the product as it was: the part split off stays in their selections.
        await self._follow(user_id, set(), [str(new_id)], keeping=str(product.id))
        await self.session.flush()

    async def _follow(
        self,
        user_id: uuid.UUID,
        gone: set[str],
        added: list[str],
        keeping: str | None = None,
    ) -> None:
        """Keep saved selections meaning what the user picked after a merge or split."""
        for selection in await self.products.selections(user_id):
            ids = list(selection.product_ids)
            touched = bool(gone & set(ids)) or (keeping is not None and keeping in ids)
            if not touched:
                continue
            ids = [i for i in ids if i not in gone]
            selection.product_ids = list(dict.fromkeys([*ids, *added]))

    async def explore(
        self, user_id: uuid.UUID, product_ids: Sequence[uuid.UUID], period: DateRange | None
    ) -> Exploration:
        """How much of these products the user bought over `period`, and at what prices (F16.2).

        `period` None is all time. Raises NotFoundError when any product is not the user's
        (N2) — another user's product is indistinguishable from none.
        """
        wanted = list(dict.fromkeys(product_ids))
        products = await self.products.owned(user_id, wanted)
        if not wanted or len(products) != len(wanted):
            raise NotFoundError("Product not found")
        order = {pid: i for i, pid in enumerate(wanted)}
        facts = [
            ProductFacts(p.id, p.name, p.size_amount, p.size_unit)
            for p in sorted(products, key=lambda p: order[p.id])
        ]
        purchases = await self.products.purchases_of(user_id, wanted, period)
        return explore(facts, purchases, (period.start, period.end) if period else None)

    async def overview(self, user_id: uuid.UUID, period: DateRange | None) -> ProductsOverview:
        """Every product's price move and each shop's standing over `period` (F23.5).

        Lines not matched yet are matched first, as the product list does.
        """
        await self.link_unmatched(user_id)
        products = await self.products.list_with_aliases(user_id)
        facts = [ProductFacts(p.id, p.name, p.size_amount, p.size_unit) for p in products]
        purchases = await self.products.purchases_of(user_id, [p.id for p in products], period)
        return products_overview(facts, purchases)

    async def save_selection(
        self,
        user_id: uuid.UUID,
        name: str,
        product_ids: Sequence[uuid.UUID],
        selection_id: uuid.UUID | None = None,
    ) -> ProductSelection:
        """Save products under a name, or change a saved selection (F16.2).

        Raises NotFoundError for a selection or product that is not the user's (N2).
        """
        wanted = list(dict.fromkeys(product_ids))
        if len(await self.products.owned(user_id, wanted)) != len(wanted):
            raise NotFoundError("Product not found")
        if selection_id is None:
            selection = ProductSelection(user_id=user_id)
            self.session.add(selection)
        else:
            found = await self.products.selection(user_id, selection_id)
            if found is None:
                raise NotFoundError("Selection not found")
            selection = found
        selection.name = name.strip()
        selection.product_ids = [str(p) for p in wanted]
        await self.session.flush()
        return selection

    async def delete_selection(self, user_id: uuid.UUID, selection_id: uuid.UUID) -> None:
        """Forget a saved selection. Raises NotFoundError when it is not the user's (N2)."""
        if not await self.products.delete_selection(user_id, selection_id):
            raise NotFoundError("Selection not found")
