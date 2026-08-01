"""Deterministic itinerary sorting (RTE-006).

PHASE.md §14: each sort defines the fixed tie-breaker chain
  selected field -> connection_count -> total_duration -> initial departure instant
  -> destination code -> itinerary ID.
The same input dataset and criteria always yield the same ordering.
"""

from __future__ import annotations

from datetime import timezone
from decimal import Decimal

from app.domain.enums import SortMode
from app.domain.itinerary import Itinerary

# A price sentinel so UNKNOWN/None estimates sort last under PRICE without using inf math.
_MAX_PRICE = Decimal("999999999")


def _tie_breakers(it: Itinerary) -> tuple[object, ...]:
    return (
        it.connection_count,
        it.total_duration_minutes,
        it.departure_at.astimezone(timezone.utc).isoformat(),
        it.destination_code,
        it.itinerary_id,
    )


def _primary(it: Itinerary, mode: SortMode) -> tuple[object, ...]:
    if mode == SortMode.PRICE:
        amount = it.price.amount if it.price.amount is not None else _MAX_PRICE
        return (amount,)
    if mode == SortMode.TOTAL_DURATION:
        return (it.total_duration_minutes,)
    if mode == SortMode.EARLIEST_DEPARTURE:
        return (it.departure_at.astimezone(timezone.utc).isoformat(),)
    if mode == SortMode.LATEST_DEPARTURE:
        # Negate by reversing via a descending key: wrap in a tuple that inverts order.
        # Represent as negative ordinal of the instant for stable ascending sort.
        return (-it.departure_at.astimezone(timezone.utc).timestamp(),)
    if mode == SortMode.DESTINATION:
        return (it.destination_code,)
    raise ValueError(f"unsupported sort mode: {mode}")


def sort_itineraries(itineraries: list[Itinerary], mode: SortMode) -> list[Itinerary]:
    return sorted(itineraries, key=lambda it: _primary(it, mode) + _tie_breakers(it))
