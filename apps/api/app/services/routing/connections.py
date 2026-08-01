"""Connection validation for one-stop itineraries (RTE-004).

PHASE.md §7–§9: layover computed on absolute instants, inclusive min/max bounds,
acyclic airport path, total-duration ceiling. See ADR-005 for the candidate-date and
inclusive-window policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from app.domain.flight_instance import FlightInstance


@dataclass(frozen=True, slots=True)
class ConnectionPolicy:
    min_connection_minutes: int
    max_connection_minutes: int
    max_total_duration_minutes: int


@dataclass(frozen=True, slots=True)
class ConnectionResult:
    is_valid: bool
    reason: str = ""
    layover_minutes: int = 0


def layover_minutes(first: FlightInstance, second: FlightInstance) -> int:
    delta = second.departure_at.astimezone(timezone.utc) - first.arrival_at.astimezone(timezone.utc)
    return int(delta.total_seconds() // 60)


def total_duration_minutes(first: FlightInstance, second: FlightInstance) -> int:
    delta = second.arrival_at.astimezone(timezone.utc) - first.departure_at.astimezone(timezone.utc)
    return int(delta.total_seconds() // 60)


def validate_connection(
    first: FlightInstance,
    second: FlightInstance,
    origin: str,
    policy: ConnectionPolicy,
) -> ConnectionResult:
    """Validate a candidate one-stop pairing. Reasons are stable, testable strings."""
    if second.origin_code != first.destination_code:
        return ConnectionResult(False, "second_origin_mismatch")

    # Acyclic path: no airport may repeat (PHASE.md §9).
    path = [origin, first.destination_code, second.destination_code]
    if len(set(path)) != len(path):
        return ConnectionResult(False, "repeated_airport")
    if second.destination_code == origin:
        return ConnectionResult(False, "return_to_origin")

    # Duplicate-segment guard.
    if second.scheduled_flight_id == first.scheduled_flight_id:
        return ConnectionResult(False, "duplicate_segment")

    lay = layover_minutes(first, second)
    if lay <= 0:
        return ConnectionResult(False, "nonpositive_layover", lay)
    if lay < policy.min_connection_minutes:
        return ConnectionResult(False, "below_min_connection", lay)
    if lay > policy.max_connection_minutes:
        return ConnectionResult(False, "above_max_connection", lay)

    total = total_duration_minutes(first, second)
    if total <= 0:
        return ConnectionResult(False, "nonpositive_total_duration", lay)
    if total > policy.max_total_duration_minutes:
        return ConnectionResult(False, "above_max_total_duration", lay)

    return ConnectionResult(True, "", lay)
