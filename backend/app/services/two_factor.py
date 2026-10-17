"""A second factor at sign-in: an authenticator app's code, or a recovery code (F18.6.1)."""

import hashlib
import io
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

import pyotp
import segno
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import DomainError, PermissionDeniedError, ProblemCode
from app.core.security import decrypt_secret, encrypt_secret, verify_password
from app.models.user import User

ISSUER = "Budget Agent"
RECOVERY_CODES = 10


def _hash(code: str) -> str:
    return hashlib.sha256(code.replace("-", "").strip().lower().encode()).hexdigest()


def new_recovery_code() -> str:
    """A code to sign in with once when the phone is lost: 10 characters, read in two halves."""
    code = secrets.token_hex(5)
    return f"{code[:5]}-{code[5:]}"


@dataclass(frozen=True)
class Setup:
    """What the screen shows to set an authenticator up: the QR code, and the key in text."""

    secret: str
    uri: str
    qr_svg: str


class TwoFactorService:
    """Setting up, using and turning off the second factor of one account.

    The secret is stored encrypted and only counts once a first code proves the app
    reads it; recovery codes are stored as hashes and each works once. Any user may turn
    it on; every admin must (F18.6.1).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def begin(self, user: User) -> Setup:
        """Start setting up: a new secret, shown as a QR code, not yet in force.

        Raises DomainError when the account already has a second factor.
        """
        if user.two_factor_enabled:
            raise DomainError(
                "Two-factor sign-in is already on.", code=ProblemCode.TWO_FACTOR_ALREADY_ON
            )
        secret = pyotp.random_base32()
        user.two_factor_secret = encrypt_secret(secret)
        await self.session.flush()
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=ISSUER)
        out = io.BytesIO()
        segno.make(uri, error="m").save(out, kind="svg", scale=5, border=2, xmldecl=False)
        return Setup(secret=secret, uri=uri, qr_svg=out.getvalue().decode())

    async def confirm(self, user: User, code: str) -> list[str]:
        """Turn it on once a code from the app matches; returns the recovery codes, once.

        Raises PermissionDeniedError (two_factor_code_wrong) for a code that does not.
        """
        if user.two_factor_secret is None or user.two_factor_enabled:
            raise DomainError("Start setting it up first.", code=ProblemCode.TWO_FACTOR_NOT_STARTED)
        if not self._code_matches(user, code):
            raise PermissionDeniedError(
                "The code is not right.", code=ProblemCode.TWO_FACTOR_CODE_WRONG
            )
        codes = [new_recovery_code() for _ in range(RECOVERY_CODES)]
        user.recovery_code_hashes = [_hash(c) for c in codes]
        user.two_factor_enabled_at = datetime.now(UTC)
        await self.session.flush()
        return codes

    async def verify(self, user: User, code: str) -> bool:
        """Whether `code` is the app's current code or an unused recovery code, spending it."""
        if not user.two_factor_enabled:
            return False
        if self._code_matches(user, code):
            return True
        hashed = _hash(code)
        left = list(user.recovery_code_hashes or [])
        if hashed not in left:
            return False
        left.remove(hashed)
        user.recovery_code_hashes = left
        await self.session.flush()
        return True

    async def turn_off(self, user: User, password: str, code: str) -> None:
        """Turn it off with the password and a code, both — a stolen session cannot.

        Raises PermissionDeniedError for a wrong password or code.
        """
        if not verify_password(password, user.password_hash) or not await self.verify(user, code):
            raise PermissionDeniedError(
                "The password or the code is not right.",
                code=ProblemCode.TWO_FACTOR_CODE_WRONG,
            )
        user.two_factor_secret = None
        user.two_factor_enabled_at = None
        user.recovery_code_hashes = None
        await self.session.flush()

    @staticmethod
    def _code_matches(user: User, code: str) -> bool:
        if user.two_factor_secret is None:
            return False
        digits = code.replace(" ", "")
        if not (digits.isdigit() and len(digits) == 6):
            return False
        # One step either side: a phone's clock is rarely exactly right.
        return pyotp.TOTP(decrypt_secret(user.two_factor_secret)).verify(digits, valid_window=1)
