"""API exception handlers producing the consistent error envelope (ADR-009).

Maps Pydantic validation errors and Phase 3 typed RoutingError subclasses to stable
public error codes + HTTP statuses. Internal exceptions become a generic 500 with no
SQL/stack-trace/secret leakage (PHASE.md §Public API Error Contract, §Security).
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.middleware import REQUEST_ID_HEADER, get_request_id
from app.domain.errors import RoutingError, RoutingErrorCode
from app.schemas.api_common import ApiErrorCode

# Phase 3 routing error code -> (HTTP status, public API error code)
_ROUTING_MAP: dict[RoutingErrorCode, tuple[int, ApiErrorCode]] = {
    RoutingErrorCode.UNKNOWN_ORIGIN: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        ApiErrorCode.INVALID_AIRPORT,
    ),
    RoutingErrorCode.INVALID_ORIGIN_TIMEZONE: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        ApiErrorCode.INVALID_REQUEST,
    ),
    RoutingErrorCode.INVALID_CRITERIA: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        ApiErrorCode.INVALID_REQUEST,
    ),
    RoutingErrorCode.DATE_OUTSIDE_SCHEDULE_RANGE: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    assert isinstance(exc, RequestValidationError)
    # Per-field details, but never echo internal object reprs.
    details = {
        "fields": [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()
        ]
    }
    return _envelope(
        request,
        http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code=ApiErrorCode.INVALID_REQUEST,
        message="The request failed validation.",
        details=details,
    )


async def routing_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Signature uses Exception for Starlette handler compatibility; narrow internally.
    assert isinstance(exc, RoutingError)
    http_status, code = _ROUTING_MAP.get(
        exc.code, (status.HTTP_500_INTERNAL_SERVER_ERROR, ApiErrorCode.INTERNAL_ERROR)
    )
    # Expected (non-500) routing errors carry a safe, human-readable message.
    message = str(exc) if http_status < 500 else "An internal error occurred."
    return _envelope(request, http_status=http_status, code=code, message=message)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak the exception detail, SQL, or a stack trace to the client.
    return _envelope(
        request,
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ApiErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
    )
