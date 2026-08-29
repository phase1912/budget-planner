from app.models.receipt import Receipt
from tests.factories.base import ModelFactory


class ReceiptFactory(ModelFactory[Receipt]):
    __model__ = Receipt
