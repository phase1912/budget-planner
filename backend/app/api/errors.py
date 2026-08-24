"""Uniform error envelope and global exception handlers (F0.2.4).

Every error response — validation, not-found, permission, or an unexpected
failure — is shaped as an RFC 7807 problem+json body carrying a stable
`code` the client can branch on, not just an HTTP status. BRD A2 and B6
both require a reason to accompany a rejection, not a bare status code;
this is the one place that reason gets attached, not each route for itself.
"""

import logging
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ProblemDetail(BaseModel):
    """RFC 7807 problem+json body, extended with a stable machine-readable `code`."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: str


class AppError(Exception):
    """Base for domain errors a route or service can raise to produce a ProblemDetail.

    A service raises a subclass; the handler registered below is the only
    place that turns it into a response, so no route builds its own error
    JSON.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    title: str = "Internal Server Error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    """A requested resource does not exist, or belongs to another user (BRD N2).

    Cross-user access is deliberately indistinguishable from a genuinely
    missing resource — a 403 would confirm the record exists.
    """

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    title = "Not Found"


class PermissionDeniedError(AppError):
    """The caller is known but not permitted to perform this action.

    Distinct from NotFoundError: this is for actions on a resource whose
    existence is not itself sensitive, only the caller's right to act on it.
    """

    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"
    title = "Permission Denied"


class RegistrationError(AppError):
    """Raised when registration fails, hiding the reason from the response (G2)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "registration_failed"
    title = "Registration Failed"


class AuthenticationError(AppError):
    """Raised on any login failure, generic by design (G4)."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_failed"
    title = "Authentication Failed"


class DomainError(AppError):
    """Raised for business logic rule violations (e.g., F1.4.2 currency lock)."""

    status_code = status.HTTP_409_CONFLICT
    code = "domain_error"
    title = "Domain Rule Violation"


_HTTP_STATUS_PROBLEMS: dict[int, tuple[str, str]] = {
    status.HTTP_400_BAD_REQUEST: ("bad_request", "Bad Request"),
    status.HTTP_401_UNAUTHORIZED: ("unauthorized", "Unauthorized"),
    status.HTTP_403_FORBIDDEN: ("permission_denied", "Permission Denied"),
    status.HTTP_404_NOT_FOUND: ("not_found", "Not Found"),
}


def _problem_response(*, status_code: int, code: str, title: str, detail: str) -> JSONResponse:
    problem = ProblemDetail(status=status_code, code=code, title=title, detail=detail)
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    return _problem_response(
        status_code=error.status_code, code=error.code, title=error.title, detail=error.detail
    )


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    error = cast(RequestValidationError, exc)
    detail = "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    )
    return _problem_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        title="Validation Error",
        detail=detail or "The request could not be validated.",
    )


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    error = cast(HTTPException, exc)
    code, title = _HTTP_STATUS_PROBLEMS.get(error.status_code, ("http_error", "HTTP Error"))
    detail = error.detail if isinstance(error.detail, str) else str(error.detail)
    return _problem_response(status_code=error.status_code, code=code, title=title, detail=detail)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    return _problem_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
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
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)
