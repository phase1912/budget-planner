from app.models.user import User
from tests.factories.base import ModelFactory


class UserFactory(ModelFactory[User]):
    __model__ = User
