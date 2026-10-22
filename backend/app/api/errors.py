"""Uniform error envelope and global exception handlers (F0.2.4).

Every error response — validation, not-found, permission, or an unexpected
failure — is shaped as an RFC 7807 problem+json body carrying a stable
`code` the client can branch on, not just an HTTP status. BRD A2 and B6
both require a reason to accompany a rejection, not a bare status code;
this is the one place that reason gets attached, not each route for itself.
"""

import enum
import logging
from collections.abc import Mapping
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ProblemCode(enum.StrEnum):
    """Every `code` an error response can carry, so the client can word each one (F9.9.5).

    The client shows its own translation of the code, filled from `params`, and falls
    back to the English `detail` for a code it does not know; a test checks every code
    here has a translation. A refusal the user reads gets its own code, not a generic one.
    """

    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    HTTP_ERROR = "http_error"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMITED = "rate_limited"
    DOMAIN_ERROR = "domain_error"
    REGISTRATION_FAILED = "registration_failed"
    WEAK_PASSWORD = "weak_password"
    AUTHENTICATION_FAILED = "authentication_failed"
    INVALID_CREDENTIALS = "invalid_credentials"
    SESSION_EXPIRED = "session_expired"
    INVALID_PERIOD = "invalid_period"
    INVALID_GOAL = "invalid_goal"
    INSUFFICIENT_DATA = "insufficient_data"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    UPLOAD_LIMIT_EXCEEDED = "upload_limit_exceeded"
    TOO_MANY_PHOTOS = "too_many_photos"
    TOO_MANY_RECEIPTS = "too_many_receipts"
    PHOTOS_TOO_LARGE = "photos_too_large"
    QUOTA_EXCEEDED = "quota_exceeded"
    SERVICE_BUSY = "service_busy"
    MESSAGE_TOO_LARGE = "message_too_large"
    CATEGORISER_UNAVAILABLE = "categoriser_unavailable"
    ADVICE_UNAVAILABLE = "advice_unavailable"
    SPEECH_UNAVAILABLE = "speech_unavailable"
    SPEECH_TOO_LONG = "speech_too_long"
    CURRENCY_LOCKED = "currency_locked"
    CATEGORY_EXISTS = "category_exists"
    CATEGORY_MOVE_TARGET = "category_move_target"
    CATEGORY_NOT_YOURS = "category_not_yours"
    EXPORT_NOT_READY = "export_not_ready"
    ALREADY_IN_HOUSEHOLD = "already_in_household"
    NOT_IN_HOUSEHOLD = "not_in_household"
    OWNER_CANNOT_LEAVE = "owner_cannot_leave"
    CANNOT_REMOVE_SELF = "cannot_remove_self"
    MEMBER_NOT_FOUND = "member_not_found"
    INVITE_INVALID = "invite_invalid"
    HOUSEHOLD_CURRENCY_MISMATCH = "household_currency_mismatch"
    OWNER_ONLY = "owner_only"
    CHILD_READ_ONLY = "child_read_only"
    OWNER_ROLE_FIXED = "owner_role_fixed"
    MONTH_CLOSED = "month_closed"
    NEEDS_CARD = "needs_card"
    SAME_ACCOUNT = "same_account"
    INVALID_CARD = "invalid_card"
    CARD_DONE = "card_done"
    TRIPS_OVERLAP = "trips_overlap"
    PER_DIEM_TIMES = "per_diem_times"
    PER_DIEM_NO_RATES = "per_diem_no_rates"
    PER_DIEM_PERSONAL_TRIP = "per_diem_personal_trip"
    INVALID_EXPORT = "invalid_export"
    EMAIL_NOT_CONFIRMED = "email_not_confirmed"
    DISPOSABLE_EMAIL = "disposable_email"
    EMAIL_DOMAIN_UNREACHABLE = "email_domain_unreachable"
    EMAIL_TAKEN = "email_taken"
    LINK_INVALID = "link_invalid"
    TERMS_REQUIRED = "terms_required"
    TWO_FACTOR_ALREADY_ON = "two_factor_already_on"
    TWO_FACTOR_NOT_STARTED = "two_factor_not_started"
    TWO_FACTOR_CODE_WRONG = "two_factor_code_wrong"
    SECOND_FACTOR_REQUIRED = "second_factor_required"
    SUPER_ADMIN_ONLY = "super_admin_only"
    ADMIN_ROLE_FIXED = "admin_role_fixed"
    ALREADY_CONFIRMED = "already_confirmed"
    DISCOUNT_TOO_LARGE = "discount_too_large"
    INCOME_UNREADABLE = "income_unreadable"
    NOT_INCOME = "not_income"


class ProblemDetail(BaseModel):
    """RFC 7807 problem+json body, extended with a stable machine-readable `code`.

    `params` holds the values `detail` was worded with — a limit, a currency — so the
    client can say the same thing in the user's language (F9.9.5).
    """

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: ProblemCode
    params: dict[str, str | int] = Field(default_factory=dict)


class AppError(Exception):
    """Base for domain errors a route or service can raise to produce a ProblemDetail.

    A service raises a subclass; the handler registered below is the only
    place that turns it into a response, so no route builds its own error
    JSON.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: ProblemCode = ProblemCode.INTERNAL_ERROR
    title: str = "Internal Server Error"

    def __init__(
        self,
        detail: str,
        *,
        code: ProblemCode | None = None,
        params: Mapping[str, str | int] | None = None,
    ) -> None:
        """`code` narrows the class's own code for one refusal; `params` fill its wording."""
        super().__init__(detail)
        self.detail = detail
        if code is not None:
            self.code = code
        self.params = dict(params or {})


class NotFoundError(AppError):
    """A requested resource does not exist, or belongs to another user (BRD N2).

    Cross-user access is deliberately indistinguishable from a genuinely
    missing resource — a 403 would confirm the record exists.
    """

    status_code = status.HTTP_404_NOT_FOUND
    code = ProblemCode.NOT_FOUND
    title = "Not Found"


class PermissionDeniedError(AppError):
    """The caller is known but not permitted to perform this action.

    Distinct from NotFoundError: this is for actions on a resource whose
    existence is not itself sensitive, only the caller's right to act on it.
    """

    status_code = status.HTTP_403_FORBIDDEN
    code = ProblemCode.PERMISSION_DENIED
    title = "Permission Denied"


class RegistrationError(AppError):
    """Raised when registration fails, hiding the reason from the response (G2)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = ProblemCode.REGISTRATION_FAILED
    title = "Registration Failed"


class AuthenticationError(AppError):
    """Raised on any login failure, generic by design (G4)."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = ProblemCode.AUTHENTICATION_FAILED
    title = "Authentication Failed"


class DomainError(AppError):
    """Raised for business logic rule violations (e.g., F1.4.2 currency lock)."""

    status_code = status.HTTP_409_CONFLICT
    code = ProblemCode.DOMAIN_ERROR
    title = "Domain Rule Violation"


class InvalidPeriodError(AppError):
    """Raised for a statistics period that ends before it starts (BRD E2)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ProblemCode.INVALID_PERIOD
    title = "Invalid Period"


class PerDiemError(AppError):
    """Raised when a business trip's per diem cannot be worked out from its times (F20.4)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ProblemCode.PER_DIEM_TIMES
    title = "Per Diem Not Worked Out"


class InvalidExportError(AppError):
    """Raised for an export whose kind and format do not go together (BRD N6, F20.5)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ProblemCode.INVALID_EXPORT
    title = "Invalid Export"


class InvalidGoalError(AppError):
    """Raised for a goal whose fields do not fit its type (BRD F1)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ProblemCode.INVALID_GOAL
    title = "Invalid Goal"


class InsufficientDataError(AppError):
    """Raised when there is not enough history to generate reliable advice (BRD F5)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ProblemCode.INSUFFICIENT_DATA
    title = "Insufficient Data"


class UnsupportedFileFormatError(AppError):
    """Raised when an uploaded file is not a supported format (BRD A2)."""

    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = ProblemCode.UNSUPPORTED_MEDIA_TYPE
    title = "Unsupported File Format"


class UploadLimitExceededError(AppError):
    """Raised when an upload exceeds photo count or size limits (BRD A4, A8)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = ProblemCode.UPLOAD_LIMIT_EXCEEDED
    title = "Upload Limit Exceeded"


class ReceiptQuotaExceededError(AppError):
    """Raised when an account has spent its AI credits for the month (F10.6, F21.9)."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = ProblemCode.QUOTA_EXCEEDED
    title = "Monthly AI Credits Spent"


class EmailNotConfirmedError(AppError):
    """The account's address is not confirmed yet, so this action waits (F17.8.2)."""

    status_code = status.HTTP_403_FORBIDDEN
    code = ProblemCode.EMAIL_NOT_CONFIRMED
    title = "Email Not Confirmed"


class EmailRefusedError(AppError):
    """An address an account cannot use: throwaway, undeliverable or taken (F17.8.3-4)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = ProblemCode.DISPOSABLE_EMAIL
    title = "Email Address Refused"


class InvalidLinkError(AppError):
    """A link from a letter that is expired, already used or not one of ours (F17.8)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = ProblemCode.LINK_INVALID
    title = "Link No Longer Valid"


class ServiceBusyError(AppError):
    """Raised when the service has read as many receipts today as it will (F10.6)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ProblemCode.SERVICE_BUSY
    title = "Service Busy"


class MessageTooLargeError(AppError):
    """Raised for an inbound email larger than receipt intake accepts (F11.2)."""

    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    code = ProblemCode.MESSAGE_TOO_LARGE
    title = "Message Too Large"


class CategoriserUnavailableError(AppError):
    """The categoriser gave no answer at all, so nothing was changed (BRD C3).

    Distinct from a completed pass that left items Uncategorized: the user
    should retry later rather than read the result as the agent's verdict.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ProblemCode.CATEGORISER_UNAVAILABLE
    title = "Categoriser Unavailable"


class AdviceUnavailableError(AppError):
    """The advice model gave no answer, so the goal's advice was left as it was (BRD F3).

    Distinct from an answer with nothing specific in it: the user should try
    again later rather than read it as "your receipts support no advice".
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ProblemCode.ADVICE_UNAVAILABLE
    title = "Advice Unavailable"


class SpeechUnavailableError(AppError):
    """The recogniser gave no answer (F21.2.2): the user can say it again, or type it."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ProblemCode.SPEECH_UNAVAILABLE
    title = "Speech Unavailable"


class SpeechTooLongError(AppError):
    """A recording longer than the microphone allows (F21.2.2)."""

    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    code = ProblemCode.SPEECH_TOO_LONG
    title = "Recording Too Long"


_HTTP_STATUS_PROBLEMS: dict[int, tuple[ProblemCode, str]] = {
    status.HTTP_400_BAD_REQUEST: (ProblemCode.BAD_REQUEST, "Bad Request"),
    status.HTTP_401_UNAUTHORIZED: (ProblemCode.UNAUTHORIZED, "Unauthorized"),
    status.HTTP_403_FORBIDDEN: (ProblemCode.PERMISSION_DENIED, "Permission Denied"),
    status.HTTP_404_NOT_FOUND: (ProblemCode.NOT_FOUND, "Not Found"),
}


def _problem_response(
    *,
    status_code: int,
    code: ProblemCode,
    title: str,
    detail: str,
    params: Mapping[str, str | int] | None = None,
) -> JSONResponse:
    problem = ProblemDetail(
        status=status_code, code=code, title=title, detail=detail, params=dict(params or {})
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    return _problem_response(
        status_code=error.status_code,
        code=error.code,
        title=error.title,
        detail=error.detail,
        params=error.params,
    )


async def _handle_rate_limited(request: Request, exc: Exception) -> JSONResponse:
    """Too many requests from one client (F10.6.3), in the envelope every error uses.

    Retry-After is the length of the limit's window: the earliest the count can have
    dropped, never later than it really frees up by more than one window.
    """
    error = cast(RateLimitExceeded, exc)
    retry_after = int(error.limit.limit.get_expiry()) if error.limit else 60
    response = _problem_response(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code=ProblemCode.RATE_LIMITED,
        title="Too Many Requests",
        detail=f"Too many requests from this address ({error.detail}). "
        f"Try again in {retry_after} seconds.",
        params={"seconds": retry_after},
    )
    response.headers["Retry-After"] = str(retry_after)
    return response


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    error = cast(RequestValidationError, exc)
    detail = "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    )
    return _problem_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code=ProblemCode.VALIDATION_ERROR,
        title="Validation Error",
        detail=detail or "The request could not be validated.",
    )


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    error = cast(HTTPException, exc)
    code, title = _HTTP_STATUS_PROBLEMS.get(
        error.status_code, (ProblemCode.HTTP_ERROR, "HTTP Error")
    )
    detail = error.detail if isinstance(error.detail, str) else str(error.detail)
    return _problem_response(status_code=error.status_code, code=code, title=title, detail=detail)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    return _problem_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ProblemCode.INTERNAL_ERROR,
        title="Internal Server Error",
        detail="An unexpected error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register every global exception handler, once, for `app`.

    Order matters only in that more specific handlers (AppError) are
    registered independently of HTTPException — Starlette dispatches by
    the closest matching type in the exception's MRO, not registration
    order, so AppError and HTTPException never compete for the same
    exception instance.
    """
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RateLimitExceeded, _handle_rate_limited)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)
