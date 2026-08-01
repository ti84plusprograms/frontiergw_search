"""Timezone-aware dated flight instance (RTE-001).

A :class:`FlightInstance` is a scheduled-flight definition resolved for one specific
operating date, with timezone-aware departure/arrival instants. See PHASE.md
§Flight-Instance Resolution and TDD §8.4.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone


@dataclass(frozen=True, slots=True)
class FlightInstance:
    scheduled_flight_id: uuid.UUID
    carrier_code: str
    flight_number: str
    origin_code: str
    destination_code: str
    departure_at: datetime
    arrival_at: datetime
    operating_date: date
    data_source_id: uuid.UUID

    def __post_init__(self) -> None:
        # All resolved datetimes must be timezone-aware (PHASE.md §Timezone Awareness).
        if self.departure_at.tzinfo is None or self.departure_at.utcoffset() is None:
            raise ValueError("departure_at must be timezone-aware")
        if self.arrival_at.tzinfo is None or self.arrival_at.utcoffset() is None:
            raise ValueError("arrival_at must be timezone-aware")
        # Duration must be positive as an absolute instant (PHASE.md §2, §10).
        if self.arrival_at <= self.departure_at:
            raise ValueError("arrival_at must be strictly after departure_at")

    @property
    def duration_minutes(self) -> int:
        """Elapsed flight time in whole minutes, computed from absolute instants.

        Uses UTC-normalized timestamps, never wall-clock subtraction (TDD §13.1).
        """
        delta = self.arrival_at.astimezone(timezone.utc) - self.departure_at.astimezone(
            timezone.utc
        )
        seconds = delta.total_seconds()
        if seconds % 60 != 0:
            raise ValueError("flight duration is not a whole number of minutes")
        return int(seconds // 60)
