"""Every refusal is `{detail, code, params}`, with a stable code (ADR-017 _Errors_).

Routes and services raise an `ApiError`; FastAPI's own 404, 405 and 422 are wrapped in
the same envelope here. A refusal never carries a submitted value, an exception's text or
a traceback; on a 422, `extra_forbidden` trims the trailing unknown key from `loc`,
remaining string `loc` segments longer than 128 characters are truncated to 127 characters
plus `"…"`, and `params.errors` is capped at 25 entries with `"truncated": true` only when
more exist (ADR-020 _CHO-053 amendments_, _DEF-040 amendments_). The two exceptions are
Starlette's middleware's plain-text refusals, a 400 for a `Host` not allowed and a 413 for
a body over the limit (`create_app`).
"""

from collections.abc import Mapping, Sequence
from enum import StrEnum
from http import HTTPStatus
from typing import Any, Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# The one reference to it: FastAPI raises it for an unknown path or method and an
# unreadable body, so its handler is registered here. Routes raise `ApiError`.
from starlette.exceptions import HTTPException  # noqa: TID251 - to register its handler

from roadmaps_api.wire import ApiResponseModel


class ErrorCode(StrEnum):
    UNAUTHENTICATED = "auth.unauthenticated"
    PERSON_MISMATCH = "auth.person_mismatch"
    FORBIDDEN = "authz.forbidden"
    ORIGIN_NOT_ALLOWED = "request.origin_not_allowed"
    UNSUPPORTED_MEDIA_TYPE = "request.unsupported_media_type"
    NOT_FOUND = "request.not_found"
    METHOD_NOT_ALLOWED = "request.method_not_allowed"
    INVALID = "request.invalid"
    SERVICE_NOT_READY = "service.not_ready"
    INTERNAL_ERROR = "server.internal_error"


# Each code's status and the English sentence its `detail` carries.
_ERRORS: Final[dict[ErrorCode, tuple[HTTPStatus, str]]] = {
    ErrorCode.UNAUTHENTICATED: (
        HTTPStatus.UNAUTHORIZED,
        "You need to sign in to continue.",
    ),
    ErrorCode.PERSON_MISMATCH: (
        HTTPStatus.CONFLICT,
        "The signed-in person does not match this request.",
    ),
    ErrorCode.FORBIDDEN: (
        HTTPStatus.FORBIDDEN,
        "You do not have permission to do this.",
    ),
    ErrorCode.ORIGIN_NOT_ALLOWED: (
        HTTPStatus.FORBIDDEN,
        "This request's origin is not allowed.",
    ),
    ErrorCode.UNSUPPORTED_MEDIA_TYPE: (
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        "The request body must be JSON.",
    ),
    ErrorCode.NOT_FOUND: (HTTPStatus.NOT_FOUND, "Nothing is found at this path."),
    ErrorCode.METHOD_NOT_ALLOWED: (
        HTTPStatus.METHOD_NOT_ALLOWED,
        "This path does not accept this method.",
    ),
    ErrorCode.INVALID: (HTTPStatus.UNPROCESSABLE_CONTENT, "The request is not valid."),
    ErrorCode.SERVICE_NOT_READY: (
        HTTPStatus.SERVICE_UNAVAILABLE,
        "The service is not ready.",
    ),
    ErrorCode.INTERNAL_ERROR: (
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "Something went wrong on the server.",
    ),
}

# The statuses FastAPI raises itself, as Starlette's HTTPException, and their codes and
# params: a 400 is a body it could not read (not UTF-8, say), before any validation.
_FASTAPI_REFUSALS: Final[dict[HTTPStatus, tuple[ErrorCode, dict[str, Any]]]] = {
    HTTPStatus.BAD_REQUEST: (
        ErrorCode.INVALID,
        {"errors": [{"loc": ["body"], "type": "body_unreadable"}]},
    ),
    HTTPStatus.NOT_FOUND: (ErrorCode.NOT_FOUND, {}),
    HTTPStatus.METHOD_NOT_ALLOWED: (ErrorCode.METHOD_NOT_ALLOWED, {}),
}


class ErrorResponse(ApiResponseModel):
    """The envelope of every refusal, as the OpenAPI document describes it."""

    detail: str
    code: ErrorCode
    params: dict[str, Any]


class ApiError(Exception):
    """A refusal with a stable code; `params` hold only what the editor's copy needs."""

    def __init__(self, code: ErrorCode, params: dict[str, Any] | None = None) -> None:
        super().__init__(code.value)
        self.code = code
        self.params = params or {}


def error_response(
    code: ErrorCode,
    params: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    status, detail = _ERRORS[code]
    return JSONResponse(
        {"detail": detail, "code": code.value, "params": params or {}},
        status_code=status,
        headers=headers,
    )


# Bounds on a 422's `params` (ADR-020 _DEF-040 amendments_).
_MAX_VALIDATION_ERRORS: Final[int] = 25
_MAX_LOC_SEGMENT_LENGTH: Final[int] = 128


def _truncate_segment(segment: str | int) -> str | int:
    if isinstance(segment, str) and len(segment) > _MAX_LOC_SEGMENT_LENGTH:
        return f"{segment[: _MAX_LOC_SEGMENT_LENGTH - 1]}…"
    return segment


def _error_location(loc: Sequence[str | int], error_type: str) -> list[str | int]:
    # An `extra_forbidden` error ends with the unknown key the caller sent (ADR-020).
    segments = loc[:-1] if error_type == "extra_forbidden" else loc
    return [_truncate_segment(segment) for segment in segments]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    def api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.code, exc.params)

    @app.exception_handler(RequestValidationError)
    def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Only `loc` and `type`: never `input` or `msg`, which can quote submitted values.
        raw_errors = exc.errors()
        errors = [
            {"loc": _error_location(error["loc"], error["type"]), "type": error["type"]}
            for error in raw_errors[:_MAX_VALIDATION_ERRORS]
        ]
        params: dict[str, Any] = {"errors": errors}
        if len(raw_errors) > _MAX_VALIDATION_ERRORS:
            params["truncated"] = True
        return error_response(ErrorCode.INVALID, params)

    @app.exception_handler(HTTPException)
    def fastapi_refusal(_request: Request, exc: HTTPException) -> JSONResponse:
        refusal = _FASTAPI_REFUSALS.get(HTTPStatus(exc.status_code))
        if refusal is None:
            # FastAPI raises no other status itself: any other is an unexpected error,
            # except the body limit's 413, raised as a route reads the body, which
            # Starlette's middleware answers in its own plain text.
            raise exc
        code, params = refusal
        # A 405's Allow header among them (RFC 9110).
        return error_response(code, params, exc.headers)
