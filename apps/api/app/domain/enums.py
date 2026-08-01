"""Enumerations for the Phase 3 routing domain.

Values mirror the TDD (§8.7, §8.8) and PHASE.md (§14 Sorting, §16 Price Summary,
§17 Availability State).
"""

from __future__ import annotations

from enum import Enum


class PriceStatus(str, Enum):
    ESTIMATED = "ESTIMATED"
    VERIFIED = "VERIFIED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class AvailabilityStatus(str, Enum):
    NOT_CHECKED = "NOT_CHECKED"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


class SortMode(str, Enum):
    """Deterministic sort modes (PHASE.md §14). Each defines stable tie-breakers."""

    PRICE = "PRICE"
    TOTAL_DURATION = "TOTAL_DURATION"
    EARLIEST_DEPARTURE = "EARLIEST_DEPARTURE"
    LATEST_DEPARTURE = "LATEST_DEPARTURE"
    DESTINATION = "DESTINATION"
