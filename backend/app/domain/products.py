"""One product across receipts: how printed line names are matched (F16.1).

A shop prints the same product its own way — "Jogurt Natural 330ml", "JOG NAT 330ML",
"JogNat330ml". A line's name is reduced to a key: lowercase words without diacritics or
punctuation, the trailing tax-class letter dropped, dates and months left out — a monthly
plan billed "October … November 3, 2026" is the same plan next month — and the package
size apart, in grams or millilitres. Two names with one key are one product. A name whose
words abbreviate another's, of the same size, is the same product too. Anything less
certain is a question for the model, and failing an answer, a product of its own the user
can merge.
"""

import difflib
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

UNITS: dict[str, tuple[str, Decimal]] = {
    "g": ("g", Decimal(1)),
    "gr": ("g", Decimal(1)),
    "kg": ("g", Decimal(1000)),
    "ml": ("ml", Decimal(1)),
    "cl": ("ml", Decimal(10)),
    "l": ("ml", Decimal(1000)),
}
_SIZE = re.compile(
    r"(?:(?P<count>\d+)\s*[x\u00d7*]\s*)?(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|gr|g|ml|cl|l)\b",
    re.IGNORECASE,
)
_CAMEL = re.compile(
    r"(?<=[a-ząćęłńóśźż])(?=[A-ZĄĆĘŁŃÓŚŹŻ])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])"
)
_TRANSLITERATE = str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "ß": "ss"})
_NUMERIC_DATE = re.compile(r"\b\d{1,4}[./-]\d{1,2}[./-]\d{1,4}\b")
MONTHS = frozenset(
    # English, then Polish as printed once diacritics are set aside: the month and "of the
    # month". Abbreviations are left out: "Jan" is also a name, "Mar" a word.
    [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "styczen",
        "luty",
        "marzec",
        "kwiecien",
        "maj",
        "czerwiec",
        "lipiec",
        "sierpien",
        "wrzesien",
        "pazdziernik",
        "listopad",
        "grudzien",
        "stycznia",
        "lutego",
        "marca",
        "kwietnia",
        "maja",
        "czerwca",
        "lipca",
        "sierpnia",
        "wrzesnia",
        "pazdziernika",
        "listopada",
        "grudnia",
    ]
)
"""Month names a line may print to say which period it was for, never what it is."""
SIMILAR_NAMES = 0.6
"""Names this alike, of one size, are worth asking the model about; below it, not."""
MAX_CANDIDATES = 5


@dataclass(frozen=True)
class Size:
    """A package size in grams or millilitres."""

    amount: Decimal
    unit: str

    def __str__(self) -> str:
        return f"{self.amount.normalize():f}{self.unit}"


@dataclass(frozen=True)
class ProductKey:
    """What a printed name says once its spelling is set aside: words and package size."""

    words: tuple[str, ...]
    size: Size | None

    @property
    def text(self) -> str:
        """The key as stored: words, then the size after a bar."""
        return " ".join(self.words) + (f"|{self.size}" if self.size else "")


def _plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.translate(_TRANSLITERATE))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def parse_size(name: str) -> tuple[Size | None, str]:
    """The package size printed in a name, and the name without it.

    "6x100g" is one pack of 600 g; "0,5l" is 500 ml. A name with no size, or two
    different ones, has none.
    """
    found = list(_SIZE.finditer(name))
    sizes: set[Size] = set()
    for match in found:
        try:
            amount = Decimal(match["amount"].replace(",", "."))
        except InvalidOperation:
            continue
        unit, factor = UNITS[match["unit"].lower()]
        count = int(match["count"]) if match["count"] else 1
        sizes.add(Size((amount * factor * count).normalize(), unit))
    rest = _SIZE.sub(" ", name)
    return (sizes.pop() if len(sizes) == 1 else None), rest


def _without_dates(words: list[str]) -> list[str]:
    """The words without months, years and the days printed beside a month.

    "pro october november 3 2026" is "pro". A name made of nothing else keeps its words:
    a key needs something to match by.
    """
    dated = {i for i, word in enumerate(words) if word in MONTHS}
    for i in list(dated):
        for j in (i - 1, i + 1):
            if 0 <= j < len(words) and words[j].isdigit() and 1 <= int(words[j]) <= 31:
                dated.add(j)
    kept = [
        word
        for i, word in enumerate(words)
        if i not in dated and not (len(word) == 4 and word.isdigit() and 2000 <= int(word) <= 2099)
    ]
    return kept or words


def product_key(name: str) -> ProductKey:
    """The key a printed line name is matched by (F16.1)."""
    split = _CAMEL.sub(" ", _NUMERIC_DATE.sub(" ", name))
    size, rest = parse_size(split)
    words = re.findall(r"[a-z0-9]+", _plain(rest).lower())
    if len(words) > 1 and len(words[-1]) == 1 and words[-1].isalpha():
        words = words[:-1]  # the tax-class letter a till prints after the name
    return ProductKey(tuple(_without_dates(words)), size)


def abbreviates(a: ProductKey, b: ProductKey) -> bool:
    """Whether one key is the other written shorter: same size, word for word a prefix.

    "jog nat|330ml" abbreviates "jogurt natural|330ml". Numbers must match exactly, and
    a word of one letter abbreviates nothing.
    """
    if a.size != b.size or len(a.words) != len(b.words) or not a.words:
        return False
    for x, y in zip(a.words, b.words, strict=True):
        if x == y:
            continue
        if x.isdigit() or y.isdigit():
            return False
        short, long = sorted((x, y), key=len)
        if len(short) < 2 or not long.startswith(short):
            return False
    return True


def candidates[P](key: ProductKey, known: Sequence[tuple[ProductKey, P]]) -> list[P]:
    """Products a key might belong to but cannot be decided by rule: for the model to judge.

    Only products of the same size, whose names are at least `SIMILAR_NAMES` alike,
    closest first, at most `MAX_CANDIDATES`.
    """
    joined = " ".join(key.words)
    scored: dict[P, float] = {}
    for other, product in known:
        if other.size != key.size:
            continue
        ratio = difflib.SequenceMatcher(None, joined, " ".join(other.words)).ratio()
        if ratio >= SIMILAR_NAMES:
            scored[product] = max(ratio, scored.get(product, 0.0))
    return sorted(scored, key=lambda p: -scored[p])[:MAX_CANDIDATES]
