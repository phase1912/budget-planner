from typing import ClassVar

from app.models.line_item import LineItem
from app.models.receipt import Receipt
from tests.factories.base import ModelFactory


class ReceiptFactory(ModelFactory[Receipt]):
    __model__ = Receipt

    # A test builds the line items it needs; generated ones would drag in
    # randomly-owned categories and users behind them.
    line_items: ClassVar[list[LineItem]] = []

    # Random fiscal numbers would make unrelated receipts look like copies of each
    # other or not at random; a test about duplicates sets them (F11.5).
    fiscal_register_id = None
    fiscal_receipt_number = None
    possible_duplicate_of_id = None

    # A receipt is in the account's currency unless a test about conversion says not (F11.7).
    original_currency = None
    original_total = None
    exchange_rate = None
    exchange_rate_date = None
    exchange_rate_source = None
