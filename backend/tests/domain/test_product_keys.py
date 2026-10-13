"""How printed line names are matched to one product (F16.1)."""

from decimal import Decimal

import pytest

from app.domain.products import Size, abbreviates, candidates, product_key


@pytest.mark.parametrize(
    ("printed", "key"),
    [
        ("Jogurt Natural 330ml", "jogurt natural|330ml"),
        ("JOG NAT 330ML", "jog nat|330ml"),
        ("JogTrusActimel6x100g", "jog trus actimel|600g"),
        ("CISOWIANKA 1,5L NG K A", "cisowianka ng k|1500ml"),
        ("Groch łuskan0,5KG", "groch luskan|500g"),
        ("But Plastik kaucja", "but plastik kaucja"),
        ("MLEKOVITA Mleko 2% 1l C", "mlekovita mleko 2|1000ml"),
    ],
)
def test_a_printed_name_is_reduced_to_its_words_and_size(printed: str, key: str) -> None:
    assert product_key(printed).text == key


def test_the_same_name_in_another_case_is_the_same_key() -> None:
    assert product_key("But Plastik kaucja").text == product_key("But plastik kaucja").text


def test_a_multipack_is_one_pack_of_the_whole_size() -> None:
    assert product_key("Cola 6x0,5l").size == Size(Decimal(3000), "ml")


def test_a_shortened_name_of_the_same_size_is_the_same_product() -> None:
    assert abbreviates(product_key("JOG NAT 330ML"), product_key("Jogurt Natural 330ml"))


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("JOG NAT 330ML", "Jogurt Natural 500ml"),  # another size
        ("Actimel 6x100g", "Actimel Truska 6x100g"),  # another variety
        ("Grzanki 987698", "Grzanki 987700"),  # another article number
    ],
)
def test_a_different_size_variety_or_article_is_not_abbreviated(a: str, b: str) -> None:
    assert not abbreviates(product_key(a), product_key(b))


def test_only_alike_names_of_the_same_size_are_put_to_the_model() -> None:
    known = [
        (product_key("Jajko Niespodzianka 20g"), "kinder"),
        (product_key("Jajko Niespodzianka 40g"), "big"),
        (product_key("Chleb Firmowy 300g"), "bread"),
    ]

    assert candidates(product_key("JajkoNiesMeltie20g"), known) == ["kinder"]
