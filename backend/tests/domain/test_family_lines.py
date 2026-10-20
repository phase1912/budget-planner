"""What the family buys, line by line (F12.11)."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.domain.family_lines import FamilyLine, bought_twice, swaps, who_buys

ME, ANNA = uuid.uuid4(), uuid.uuid4()


def line(member: uuid.UUID, day: int, name: str, price: str, shop: str = "Lidl") -> FamilyLine:
    return FamilyLine(
        member_id=member,
        day=date(2026, 10, day),
        name=name,
        shop=shop,
        unit_price=Decimal(price),
        quantity=Decimal(1),
        paid=Decimal(price),
    )


def test_two_members_buying_one_product_within_three_days_bought_it_twice() -> None:
    found = bought_twice([line(ME, 6, "Chleb 500g", "5.00"), line(ANNA, 7, "CHLEB 500G", "5.00")])

    assert [(t.name, set(t.members), t.paid) for t in found] == [
        ("CHLEB 500G", {ME, ANNA}, Decimal("10.00"))
    ]


def test_one_person_buying_bread_every_other_day_is_a_habit_not_a_double() -> None:
    assert bought_twice([line(ME, 6, "Chleb", "5.00"), line(ME, 7, "Chleb", "5.00")]) == []


def test_four_days_apart_is_two_separate_purchases() -> None:
    assert bought_twice([line(ME, 1, "Mleko", "4.00"), line(ANNA, 5, "Mleko", "4.00")]) == []


def test_who_buys_splits_each_product_by_member_biggest_first() -> None:
    products = who_buys(
        [line(ME, 1, "Mleko", "4.00"), line(ANNA, 2, "Mleko", "4.00"), line(ME, 3, "Kawa", "30.00")]
    )

    assert [(p.name, p.total, p.members) for p in products] == [
        ("Kawa", Decimal("30.00"), {ME: Decimal("30.00")}),
        ("Mleko", Decimal("8.00"), {ME: Decimal("4.00"), ANNA: Decimal("4.00")}),
    ]


def test_a_swap_saves_the_difference_on_what_the_family_buys_a_month() -> None:
    lines = [
        line(ANNA, 2, "Mleko", "3.00", shop="Lidl"),
        *(line(ME, day, "Mleko", "4.00", shop="Zabka") for day in (5, 10, 15, 20)),
    ]

    found = swaps(lines, Decimal(1), date(2026, 10, 20), timedelta(days=60))

    assert [(s.name, s.shop, s.instead_of, s.monthly_saving) for s in found] == [
        ("Mleko", "Lidl", "Zabka", Decimal("5"))
    ]
