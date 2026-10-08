from polyfactory import Use

from app.domain.email_intake import new_forwarding_token
from app.models.user import User
from tests.factories.base import ModelFactory


class UserFactory(ModelFactory[User]):
    __model__ = User

    forwarding_token = Use(new_forwarding_token)
