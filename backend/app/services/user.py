"""User profile service (F1.4)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError
from app.domain.email_intake import new_forwarding_token
from app.models.user import User
from app.repository.receipt import ReceiptRepository
from app.repository.user import UserRepository
from app.schemas.user import UserUpdateRequest


class UserService:
    """Business logic for user profiles."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)
        self.receipt_repository = ReceiptRepository(session)

    async def update_profile(self, user: User, request: UserUpdateRequest) -> User:
        """Update user preferences (F1.4.1)."""
        data = request.model_dump(exclude_unset=True)

        if not data:
            return user

        if "currency" in data and data["currency"] != user.currency:
            # F1.4.2: explicit guard rejecting a currency change once receipts exist
            has_receipts = await self.receipt_repository.exists_for_user(user.id)
            if has_receipts:
                raise DomainError("Cannot change currency once receipts exist.")

        self.repository.update(user, data)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def regenerate_forwarding_address(self, user: User) -> User:
        """Give the user a new forwarding address; the old one stops working at once (F11.2).

        For when the address has leaked and spam reaches it. Mail already accepted
        is not affected.
        """
        user.forwarding_token = new_forwarding_token()
        await self.session.commit()
        await self.session.refresh(user)
        return user
