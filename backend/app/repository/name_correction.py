import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.categories import normalise_name
from app.models.name_correction import NameCorrection


class NameCorrectionRepository:
    """The user's remembered line-name corrections (F15.3); every query names the user (N2)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for(self, user_id: uuid.UUID) -> Sequence[NameCorrection]:
        """Every correction this user has made; never another user's (N2)."""
        stmt = select(NameCorrection).where(NameCorrection.user_id == user_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def remember(
        self, user_id: uuid.UUID, merchant_name: str | None, read_name: str, corrected_name: str
    ) -> NameCorrection | None:
        """Remember that this shop's `read_name` means `corrected_name`; the latest word wins.

        Nothing is remembered without a merchant to tie it to, or when the new name is
        what was printed — that is the user undoing a correction, not making one.
        """
        merchant = normalise_name(merchant_name)
        read = normalise_name(read_name)
        corrected = corrected_name.strip()
        if not merchant or not read or not corrected or normalise_name(corrected) == read:
            return None
        stmt = select(NameCorrection).where(
            NameCorrection.user_id == user_id,
            NameCorrection.merchant_name == merchant,
            NameCorrection.read_name == read,
        )
        correction = (await self.session.execute(stmt)).scalar_one_or_none()
        if correction is None:
            correction = NameCorrection(user_id=user_id, merchant_name=merchant, read_name=read)
            self.session.add(correction)
        correction.corrected_name = corrected
        await self.session.flush()
        return correction

    async def forget(self, user_id: uuid.UUID, merchant_name: str | None, read_name: str) -> None:
        """Stop correcting this shop's `read_name` on later receipts (F15.3.2)."""
        await self.session.execute(
            delete(NameCorrection).where(
                NameCorrection.user_id == user_id,
                NameCorrection.merchant_name == normalise_name(merchant_name),
                NameCorrection.read_name == normalise_name(read_name),
            )
        )
