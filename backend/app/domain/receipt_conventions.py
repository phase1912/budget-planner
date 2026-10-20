# ruff: noqa: RUF001 — receipts are printed in Cyrillic too; its letters are meant.
"""How receipts are printed across Europe: rules for any receipt, words per country, notes
per chain (F15.5, BRD A9-A11).

The reader's prompt is built from this table and the reconciliation rules take their words
from it, so a country added here is understood by both. Words are matched as the start of
a word, ignoring case: "rabat" also finds "Rabaty". Notes per chain are kept for what a
chain prints its own way; anything true of every receipt belongs in `GENERAL_RULES`.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    """The words one country's receipts use for the lines that are easy to misread."""

    code: str
    currency: str
    discount: tuple[str, ...]
    """A negative line under the product it reduces."""
    deposit: tuple[str, ...]
    """Returnable packaging paid on top: a positive line."""
    deposit_return: tuple[str, ...]
    """Packaging handed back: a negative line."""
    rounding: tuple[str, ...]
    """The till rounding the amount to pay: a line, with its sign."""
    totals: tuple[str, ...]
    """Subtotals, totals and tax summaries: never lines."""
    payments: tuple[str, ...]
    """How it was paid and the change given: never lines."""
    tax_marks: str
    """How a line's VAT rate is marked, left out of its amount."""


@dataclass(frozen=True)
class Shop:
    """What one chain prints differently from the rest of its country."""

    names: tuple[str, ...]
    note: str


GENERAL_RULES = """\
Receipts come from many countries; these rules hold whatever the language.
- A line item is something bought: its name, quantity, unit price and total as printed. \
A name may run over two or three lines with the quantity and prices on the last or on a \
line of their own ("2 x 3,49" or "0,532 kg x 12,99 = 6,91" above or below the name): \
join them into one item. Barcodes, article numbers and VAT summaries are not part of a name.
- Weighed goods: quantity is the weight, unit_price the price per kg or l.
- A discount printed under a product is a line item of its own with a NEGATIVE total, \
named as printed; the product keeps its full price. A footer line that sums the \
discounts ("total savings", "you saved") repeats them and is NEVER a line item.
- Returnable-packaging deposits are line items with a positive total; packaging handed \
back is a line with a negative total. A section heading or sum over deposits is no line.
- The till's rounding of the amount to pay is a line item, with its sign, named as printed.
- Menus and sets (fast food, lunch deals): the menu is one line with its price; its \
parts printed under it, indented, with no price or 0.00, are NOT line items. A part \
printed with a price of its own (a bigger size, an extra sauce, an added item) IS a line \
item of its own, even when indented under the menu: two prices are two items.
- Subtotals, totals, VAT tables and payment lines (cash, card, change, points or vouchers \
used to pay) are never line items.
- receipt_total is the receipt's total to pay, before any points, voucher or gift card \
used to pay it. When a goods subtotal and an amount to pay are both printed, take the \
amount to pay.
- VAT marks printed after an amount (a letter, a digit or a rate) are not part of it.
"""

COUNTRIES: tuple[Country, ...] = (
    Country(
        "PL",
        "PLN",
        discount=("opust", "rabat", "upust", "promocja", "zniżka", "obniżka"),
        deposit=("kaucja", "opakowania zwrotne"),
        deposit_return=("zwrot kaucji",),
        rounding=("zaokrąglenie",),
        totals=(
            "suma",
            "suma pln",
            "sprzedaż opodatkowana",
            "ptu",
            "razem",
            "do zapłaty",
            "wydania",
        ),
        payments=("gotówka", "karta", "płatność", "reszta", "bon"),
        tax_marks='a letter A-G after the amount ("7,49A"); "Sprzedaż opodatkowana A" and '
        '"PTU A 23%" are the VAT table',
    ),
    Country(
        "UA",
        "UAH",
        discount=("знижка", "знижки", "акція", "економія", "скидка"),
        deposit=("тара", "застава"),
        deposit_return=("повернення тари",),
        rounding=("округлення",),
        totals=("сума", "разом", "всього", "до сплати", "пдв", "акциз"),
        payments=("готівка", "картка", "безготівкова", "оплата", "решта", "бали", "бонус"),
        tax_marks='a letter (А, Б, В…) after the amount; "ПДВ А = 20%" is the VAT table; '
        "ФН, ЧЕК №, ЗН are the receipt's numbers, not lines",
    ),
    Country(
        "DE",
        "EUR",
        discount=("rabatt", "preisvorteil", "nachlass", "coupon", "aktion", "sofortrabatt"),
        deposit=("pfand",),
        deposit_return=("leergut", "pfandrückgabe", "pfandbon"),
        rounding=("rundung",),
        totals=("zwischensumme", "summe", "gesamt", "zu zahlen", "mwst", "netto", "brutto"),
        payments=("bar", "ec-karte", "kartenzahlung", "girocard", "gegeben", "rückgeld"),
        tax_marks='a letter after the amount ("1,99 A"); "MwSt A 19%" and "B 7%" are the VAT table',
    ),
    Country(
        "AT",
        "EUR",
        discount=("rabatt", "aktion", "preisvorteil", "jö bonus"),
        deposit=("pfand",),
        deposit_return=("leergut", "pfandrückgabe"),
        rounding=("rundung",),
        totals=("zwischensumme", "summe", "gesamt", "zu zahlen", "ust", "mwst"),
        payments=("bar", "bankomat", "karte", "gegeben", "rückgeld"),
        tax_marks='a letter after the amount; "USt 20%" and "10%" are the VAT table',
    ),
    Country(
        "CH",
        "CHF",
        discount=("rabatt", "aktion", "rabais", "réduction", "cumulus"),
        deposit=("depot", "pfand", "consigne"),
        deposit_return=("depotrückgabe", "retour"),
        rounding=("rundung", "arrondi"),
        totals=("zwischentotal", "total", "summe", "mwst", "tva"),
        payments=("bar", "karte", "twint", "rückgeld", "espèces", "carte"),
        tax_marks='a digit or letter after the amount; "MWST 8.1%" and "2.6%" are the VAT table',
    ),
    Country(
        "CZ",
        "CZK",
        discount=("sleva", "akce", "zvýhodnění"),
        deposit=("záloha", "zálohovaný", "obaly", "vratné"),
        deposit_return=("vrácení zálohy", "vratka"),
        rounding=("zaokrouhlení",),
        totals=("mezisoučet", "celkem", "k úhradě", "k platbě", "dph", "základ"),
        payments=("hotově", "hotovost", "karta", "platební karta", "vráceno", "vrátit"),
        tax_marks='a letter or rate after the amount; "DPH 21%" and "12%" are the VAT table',
    ),
    Country(
        "SK",
        "EUR",
        discount=("zľava", "akcia"),
        deposit=("záloha", "zálohovaný"),
        deposit_return=("vrátenie zálohy",),
        rounding=("zaokrúhlenie",),
        totals=("medzisúčet", "spolu", "celkom", "k úhrade", "dph", "základ"),
        payments=("hotovosť", "karta", "platobná karta", "vrátené"),
        tax_marks='a letter or rate after the amount; "DPH 23%" is the VAT table',
    ),
    Country(
        "FR",
        "EUR",
        discount=("remise", "réduction", "promo", "avantage", "bon de réduction"),
        deposit=("consigne",),
        deposit_return=("déconsigne", "retour consigne"),
        rounding=("arrondi",),
        totals=("sous-total", "total", "total à payer", "net à payer", "tva"),
        payments=("espèces", "cb", "carte bancaire", "rendu", "monnaie"),
        tax_marks='a code (1, 2…) beside the line; "TVA 5,5%" and "20%" are the VAT table',
    ),
    Country(
        "NL",
        "EUR",
        discount=("korting", "bonus", "actie", "voordeel"),
        deposit=("statiegeld",),
        deposit_return=("statiegeld retour", "emballage"),
        rounding=("afronding",),
        totals=("subtotaal", "totaal", "te betalen", "btw"),
        payments=("contant", "pin", "pinnen", "betaald", "wisselgeld"),
        tax_marks='a letter or rate after the amount; "BTW 9%" and "21%" are the VAT table',
    ),
    Country(
        "DK",
        "DKK",
        discount=("rabat", "tilbud"),
        deposit=("pant",),
        deposit_return=("returpant", "pant retur"),
        rounding=("afrunding", "øreafrunding"),
        totals=("subtotal", "i alt", "total", "at betale", "moms"),
        payments=("kontant", "kort", "dankort", "mobilepay", "byttepenge"),
        tax_marks='VAT is included; "Heraf moms 25%" is the VAT note, not a line',
    ),
    Country(
        "SE",
        "SEK",
        discount=("rabatt", "erbjudande", "extrapris"),
        deposit=("pant",),
        deposit_return=("pantretur", "returpant"),
        rounding=("öresavrundning", "avrundning"),
        totals=("delsumma", "totalt", "summa", "att betala", "moms"),
        payments=("kontant", "kort", "swish", "växel", "betalt"),
        tax_marks='VAT is included; "Moms 12%" and "25%" are the VAT table',
    ),
)

SHOPS: tuple[Shop, ...] = (
    Shop(
        ("mcdonald",),
        "Each menu is a priced line with its parts indented under it at no price: the parts "
        "are not lines. An indented part with its own price (a larger size, an extra) is a "
        "line of its own.",
    ),
    Shop(
        ("biedronka",),
        '"OPUST" under a product is its discount; deposits sit under "OPAKOWANIA ZWROTNE" and '
        "are each listed once.",
    ),
    Shop(
        ("lidl",),
        '"Lidl Plus" discounts are negative lines under the product; a multi-buy discount '
        "too. Quantities are printed on a line of their own above the product.",
    ),
    Shop(
        ("albert heijn", "ah to go"),
        '"BONUS" lines with a minus are discounts; "Bonus Box" and "Koopzegels" are not '
        "purchases of goods.",
    ),
)


SHORT = 5
"""Words shorter than this must match whole: "pant" is not "Pantene", "сума" not "сумка"."""


def _starts(words: Iterable[str]) -> re.Pattern[str]:
    """Any of `words` at the start of a word, the short ones only whole, ignoring case."""
    alternatives = (
        re.escape(w) + (r"\b" if len(w) < SHORT else "")
        for w in sorted(set(words), key=len, reverse=True)
    )
    return re.compile(r"\b(?:" + "|".join(alternatives) + ")", re.IGNORECASE)


DISCOUNT_WORDS = _starts([*(w for c in COUNTRIES for w in c.discount), "discount"])
DEPOSIT_WORDS = _starts(
    [*(w for c in COUNTRIES for w in (*c.deposit, *c.deposit_return)), "deposit", "zastaw"]
)
ROUNDING_WORDS = _starts(w for c in COUNTRIES for w in c.rounding)
TOTAL_WORDS = _starts(w for c in COUNTRIES for w in c.totals)


def prompt_notes() -> str:
    """The rules for any receipt, then each country's words and each chain's habits."""
    countries = "\n".join(
        f"- {c.code} ({c.currency}): discount {', '.join(c.discount)}; deposit "
        f"{', '.join(c.deposit)}; deposit back {', '.join(c.deposit_return)}; rounding "
        f"{', '.join(c.rounding)}; totals, never lines: {', '.join(c.totals)}; payments, "
        f"never lines: {', '.join(c.payments)}; VAT: {c.tax_marks}."
        for c in COUNTRIES
    )
    shops = "\n".join(f"- {' / '.join(s.names)}: {s.note}" for s in SHOPS)
    return (
        f"{GENERAL_RULES}\nWords by country (match the receipt's language):\n{countries}\n"
        f"Chains that print their own way:\n{shops}\n"
    )
