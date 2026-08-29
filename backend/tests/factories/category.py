from app.models.category import Category
from tests.factories.base import ModelFactory


class CategoryFactory(ModelFactory[Category]):
    __model__ = Category
