from app.models.line_item import LineItem
from tests.factories.base import ModelFactory


class LineItemFactory(ModelFactory[LineItem]):
    __model__ = LineItem
    category_id = None
