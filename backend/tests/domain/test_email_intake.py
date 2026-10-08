"""Forwarding addresses and reading inbound messages (F11.2)."""

from email.message import EmailMessage

from app.domain.email_intake import (
    forwarding_address,
    html_to_text,
    parse_message,
    token_from_address,
)


def test_an_address_gives_back_its_token_only_on_the_intake_domain() -> None:
    address = forwarding_address("ab12", "inbound.test")

    assert token_from_address(f"Budget <{address.upper()}>", "inbound.test") == "ab12"
    assert token_from_address(address, "elsewhere.test") is None
    assert token_from_address("someone@inbound.test", "inbound.test") is None
    assert token_from_address("receipts-@inbound.test", "inbound.test") is None


def test_html_is_reduced_to_its_words_one_row_per_line() -> None:
    html = (
        "<html><head><style>td {color: red}</style></head><body>"
        "<script>track()</script><table><tr><td>Woda</td><td>2,50</td></tr>"
        "<tr><td>Kawa</td><td>10,00</td></tr></table><p>Suma  12,50</p></body></html>"
    )

    assert html_to_text(html) == "Woda 2,50\nKawa 10,00\nSuma 12,50"


def test_only_attachments_the_parser_can_read_are_kept() -> None:
    message = EmailMessage()
    message["From"] = "Shopper <Shopper@Example.com>"
    message["Message-ID"] = "<m1@shop>"
    message.set_content("Hello")
    message.add_attachment(b"%PDF", maintype="application", subtype="pdf", filename="r.pdf")
    message.add_attachment(b"zip", maintype="application", subtype="zip", filename="r.zip")

    email = parse_message(message.as_bytes())

    assert (email.sender, email.message_id, email.text) == (
        "shopper@example.com",
        "<m1@shop>",
        "Hello",
    )
    assert [(a.content_type, a.content) for a in email.attachments] == [
        ("application/pdf", b"%PDF")
    ]
