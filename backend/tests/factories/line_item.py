from app.models.line_item import LineItem
from tests.factories.base import ModelFactory


class LineItemFactory(ModelFactory[LineItem]):
    __model__ = LineItem

    # Both relationships are left unset so a line item never drags a randomly
    # owned receipt or category into the database behind it. A test that needs
    # either one creates it and passes the id.
    category_id = None
    category = None
    receipt = None
    # Unmatched until the products list matches it (F16.1); never a random product.
    product_id = None
    # As read, with no score kept, nothing printed differently and nothing corrected.
    read_confidence = None
    read_name = None
    user_corrected = False
    # Automatic is the normal case; a test about a manual override says so.
    is_category_manual = False
