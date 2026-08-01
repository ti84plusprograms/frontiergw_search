"""Itinerary deduplication (RTE-005), implementing ADR-004.

Itineraries sharing the same deterministic identity are collapsed to one deterministic
winner, chosen by a total order over non-identity fields so selection is never
arbitrary. Deduplication is idempotent. Distinct itineraries are never collapsed.
"""

from __future__ import annotations

from app.domain.itinerary import Itinerary


def _winner_key(itinerary: Itinerary) -> tuple[tuple[str, ...], tuple[str, ...]]:
    # (1) smallest tuple of underlying scheduled_flight_ids, then
    # (2) smallest tuple of equipment/flight-number surrogate. equipment_code is not
    # carried on FlightInstance, so we use scheduled_flight_id (stable, total) which
    # fully orders candidates deterministically (ADR-004).
    ids = tuple(str(seg.flight.scheduled_flight_id) for seg in itinerary.segments)
    numbers = tuple(seg.flight.flight_number for seg in itinerary.segments)
    return (ids, numbers)


def deduplicate(itineraries: list[Itinerary]) -> list[Itinerary]:
    """Collapse same-identity itineraries; keep first-seen order of distinct IDs."""
    winners: dict[str, Itinerary] = {}
    order: list[str] = []
    for itinerary in itineraries:
        key = itinerary.itinerary_id
        existing = winners.get(key)
        if existing is None:
            winners[key] = itinerary
            order.append(key)
        elif _winner_key(itinerary) < _winner_key(existing):
            winners[key] = itinerary
    return [winners[key] for key in order]
