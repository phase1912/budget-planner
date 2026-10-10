import uuid

from polyfactory import Use

from app.domain.email_intake import new_forwarding_token
from app.models.user import User
from tests.factories.base import ModelFactory


class UserFactory(ModelFactory[User]):
    __model__ = User

    forwarding_token = Use(new_forwarding_token)
    # Random strings can repeat — even two empty ones — and the email is unique.
    email = Use(lambda: f"user-{uuid.uuid4().hex}@example.com")
    # An admin has no receipt quota (F10.6); a random role would make that random.
    role = "user"
