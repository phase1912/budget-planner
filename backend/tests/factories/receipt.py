from typing import ClassVar

from app.models.line_item import LineItem
from app.models.receipt import Receipt
from tests.factories.base import ModelFactory


class ReceiptFactory(ModelFactory[Receipt]):
    __model__ = Receipt

    # A test builds the line items it needs; generated ones would drag in
    # randomly-owned categories and users behind them.
    line_items: ClassVar[list[LineItem]] = []
