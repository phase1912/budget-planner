"""Contact form payload (F17.10.2)."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import Language
from app.services.contact import ContactTopic


class ContactRequest(BaseModel):
    """A message to the people running the service; `website` is a trap for bots."""

    email: EmailStr
    topic: ContactTopic
    message: str = Field(min_length=10, max_length=4000)
    language: Language | None = None
    website: str = Field(default="", max_length=200)
