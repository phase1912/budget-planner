import uuid
from datetime import UTC, datetime

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
    # Not chosen, as on a new account, unless a test about languages says otherwise (F9.9).
    language = None
    # Confirmed, as every account before F17.8 is; a test about confirmation says otherwise.
    email_confirmed_at = Use(lambda: datetime.now(UTC))
    # Off, as on a new account; a random secret would ask every sign-in for a code (F18.6.1).
    two_factor_secret = None
    two_factor_enabled_at = None
    recovery_code_hashes = None
    # A new account's look and setup (F23): the default palette, not onboarded yet.
    palette = None
    dark_at_night = False
    onboarded_at = None
    travels_for_work = False
    usual_income = None
    payday = None
    starting_balance = None
    balance_since = None
