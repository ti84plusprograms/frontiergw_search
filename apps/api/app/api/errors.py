"""API exception handlers producing the consistent error envelope (ADR-009).

Maps Pydantic validation errors and Phase 3 typed RoutingError subclasses to stable
public error codes + HTTP statuses. Internal exceptions become a generic 500 with no
SQL/stack-trace/secret leakage (PHASE.md §Public API Error Contract, §Security).
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.middleware import REQUEST_ID_HEADER, get_request_id
from app.core.monitoring import capture_exception
from app.core.observability import log_event
from app.domain.errors import RoutingError, RoutingErrorCode
from app.schemas.api_common import ApiErrorCode
from app.services.rate_limit import RateLimitExceeded

# Phase 3 routing error code -> (HTTP status, public API error code)
_ROUTING_MAP: dict[RoutingErrorCode, tuple[int, ApiErrorCode]] = {
    RoutingErrorCode.UNKNOWN_ORIGIN: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        ApiErrorCode.INVALID_AIRPORT,
    ),
    RoutingErrorCode.INVALID_ORIGIN_TIMEZONE: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        ApiErrorCode.INVALID_REQUEST,
    ),
    RoutingErrorCode.INVALID_CRITERIA: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        ApiErrorCode.INVALID_REQUEST,
    ),
    RoutingErrorCode.DATE_OUTSIDE_SCHEDULE_RANGE: (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        ApiErrorCode.DATE_OUTSIDE_SCHEDULE_RANGE,
    ),
    RoutingErrorCode.NO_ACTIVE_SCHEDULE: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        ApiErrorCode.NO_ACTIVE_SCHEDULE,
    ),
    RoutingErrorCode.INTERNAL_INVARIANT: (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        ApiErrorCode.INTERNAL_ERROR,
    ),
}


def _envelope(
    request: Request,
    *,
    http_status: int,
    code: ApiErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = get_request_id(request)
    body = {
        "error": {
            "code": code.value,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }
    return JSONResponse(
        status_code=http_status,
        content=body,
        headers={REQUEST_ID_HEADER: request_id},
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Signature uses Exception for Starlette handler compatibility; narrow internally.
    validation_error = cast(RequestValidationError, exc)
    # Per-field details, but never echo internal object reprs.
    details = {
        "fields": [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
            for e in validation_error.errors()
        ]
    }
    return _envelope(
        request,
        http_status=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code=ApiErrorCode.INVALID_REQUEST,
        message="The request failed validation.",
        details=details,
    )


async def routing_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Signature uses Exception for Starlette handler compatibility; narrow internally.
    routing_error = cast(RoutingError, exc)
    http_status, code = _ROUTING_MAP.get(
        routing_error.code, (status.HTTP_500_INTERNAL_SERVER_ERROR, ApiErrorCode.INTERNAL_ERROR)
    )
    # Expected (non-500) routing errors carry a safe, human-readable message.
    message = str(routing_error) if http_status < 500 else "An internal error occurred."
    return _envelope(request, http_status=http_status, code=code, message=message)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak the exception detail, SQL, or a stack trace to the client.
    request_id = get_request_id(request)
    capture_exception(exc, request_id)
    log_event(
        "unexpected_error",
        request_id=request_id,
        path=request.url.path,
        error_code=ApiErrorCode.INTERNAL_ERROR.value,
        failure_category=type(exc).__name__,
    )
    return _envelope(
        request,
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ApiErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    http_error = cast(HTTPException, exc)
    code = (
        ApiErrorCode.INVALID_REQUEST
        if http_error.status_code < 500
        else ApiErrorCode.INTERNAL_ERROR
    )
    message = (
        "The requested resource was not found."
        if http_error.status_code == 404
        else str(http_error.detail)
    )
    return _envelope(request, http_status=http_error.status_code, code=code, message=message)


async def rate_limit_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    rate_limit_error = cast(RateLimitExceeded, exc)
    response = _envelope(
        request,
        http_status=status.HTTP_429_TOO_MANY_REQUESTS,
        code=ApiErrorCode.RATE_LIMITED,
        message="Too many requests. Please retry later.",
        details={"retry_after_seconds": rate_limit_error.result.retry_after},
    )
    response.headers["Retry-After"] = str(rate_limit_error.result.retry_after)
    response.headers["X-RateLimit-Limit"] = str(rate_limit_error.result.limit)
    response.headers["X-RateLimit-Remaining"] = "0"
    return response
