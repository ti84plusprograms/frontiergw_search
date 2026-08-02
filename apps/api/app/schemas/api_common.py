"""Shared public API envelope schemas: errors and warnings.

Implements the consistent error contract from PHASE.md §Public API Error Contract
(and ADR-009). Public, stable enum strings; internal details never leak.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApiErrorCode(str, Enum):
    """Stable public error codes (PHASE.md §Public API Error Contract)."""

    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_AIRPORT = "INVALID_AIRPORT"
    INVALID_DEPARTURE_DATE = "INVALID_DEPARTURE_DATE"
    DATE_OUTSIDE_SCHEDULE_RANGE = "DATE_OUTSIDE_SCHEDULE_RANGE"
    NO_ACTIVE_SCHEDULE = "NO_ACTIVE_SCHEDULE"
    INVALID_CONNECTION_RANGE = "INVALID_CONNECTION_RANGE"
    INVALID_TIME_FILTER = "INVALID_TIME_FILTER"
    INVALID_PRICE_FILTER = "INVALID_PRICE_FILTER"
    UNSUPPORTED_SORT = "UNSUPPORTED_SORT"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class WarningCode(str, Enum):
    """Stable public warning codes attached to successful responses."""

    AVAILABILITY_NOT_CHECKED = "AVAILABILITY_NOT_CHECKED"
    NO_MATCHING_ITINERARIES = "NO_MATCHING_ITINERARIES"
    RESULTS_TRUNCATED = "RESULTS_TRUNCATED"


class ApiWarning(BaseModel):
    code: WarningCode
    message: str


class ApiError(BaseModel):
    code: ApiErrorCode
    message: str
    details: dict[str, Any] | None = None
    request_id: str


class ApiErrorResponse(BaseModel):
    """The single error envelope for all non-2xx API responses."""

    error: ApiError = Field(...)


# Reusable OpenAPI documentation for the error envelope, attached to endpoints so the
# error schema (and ApiErrorCode enum) appear in the generated contract.
ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    422: {"model": ApiErrorResponse, "description": "Validation error"},
    429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
    500: {"model": ApiErrorResponse, "description": "Internal error"},
    503: {"model": ApiErrorResponse, "description": "No active schedule"},
}
