"""Typed routing-domain errors and diagnostics.

PHASE.md §Error and Diagnostic Requirements: routing failures must distinguish
categories and expected no-result cases must not be treated as internal errors.
The service layer raises these typed exceptions (or returns typed results) so a
later API phase can translate them without inspecting message strings.
"""

from __future__ import annotations

from enum import Enum


class RoutingErrorCode(str, Enum):
    INVALID_CRITERIA = "INVALID_CRITERIA"
    UNKNOWN_ORIGIN = "UNKNOWN_ORIGIN"
    INVALID_ORIGIN_TIMEZONE = "INVALID_ORIGIN_TIMEZONE"
    NO_ACTIVE_SCHEDULE = "NO_ACTIVE_SCHEDULE"
    DATE_OUTSIDE_SCHEDULE_RANGE = "DATE_OUTSIDE_SCHEDULE_RANGE"
    INTERNAL_INVARIANT = "INTERNAL_INVARIANT"


class RoutingError(Exception):
    """Base class for routing-domain failures that are NOT expected no-result cases.

    ``NO_APPLICABLE_DEPARTURES`` and ``NO_ITINERARIES_AFTER_FILTER`` are represented
    as an empty result list, not as exceptions (PHASE.md: expected no-result cases
    must not be treated as internal server errors).
    """

    code: RoutingErrorCode = RoutingErrorCode.INTERNAL_INVARIANT

    def __init__(self, message: str, *, code: RoutingErrorCode | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class InvalidCriteriaError(RoutingError):
    code = RoutingErrorCode.INVALID_CRITERIA


class UnknownOriginError(RoutingError):
    code = RoutingErrorCode.UNKNOWN_ORIGIN


class InvalidTimezoneError(RoutingError):
    code = RoutingErrorCode.INVALID_ORIGIN_TIMEZONE


class NoActiveScheduleError(RoutingError):
    code = RoutingErrorCode.NO_ACTIVE_SCHEDULE


class DateOutsideScheduleRangeError(RoutingError):
    code = RoutingErrorCode.DATE_OUTSIDE_SCHEDULE_RANGE
