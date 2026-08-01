"""Itinerary domain model: segments, price summary, and deterministic identity.

PHASE.md §5–§6 (itinerary shape), §10 (duration invariants), §11 (deterministic
identity), §16 (price summary), §17 (availability). TDD §8.5–§8.7.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.domain.enums import AvailabilityStatus, PriceStatus
from app.domain.flight_instance import FlightInstance

ESTIMATE_DISCLAIMER = (
    "Estimated GoWild cost. Final taxes, fees, and availability must be confirmed with Frontier."
)


@dataclass(frozen=True, slots=True)
class PriceSummary:
    """Estimated (Phase 3) price. Never labeled verified/live (PHASE.md §15–§16)."""

    currency: str
    segment_count: int
    status: PriceStatus = PriceStatus.ESTIMATED
    amount: Decimal | None = None
    base_amount: Decimal | None = None
    taxes_and_fees: Decimal | None = None
    verified_at: datetime | None = None
    disclaimer: str = ESTIMATE_DISCLAIMER

    def __post_init__(self) -> None:
        if self.amount is not None and not isinstance(self.amount, Decimal):
            raise TypeError("PriceSummary.amount must be Decimal or None, never float")
        # Phase 3 never produces verified pricing.
        if self.status == PriceStatus.ESTIMATED and self.verified_at is not None:
            raise ValueError("estimated pricing must not carry a verified_at timestamp")


@dataclass(frozen=True, slots=True)
class ItinerarySegment:
    sequence: int
    flight: FlightInstance

    @property
    def duration_minutes(self) -> int:
        return self.flight.duration_minutes


@dataclass(frozen=True, slots=True)
class Itinerary:
    origin_code: str
    destination_code: str
    segments: tuple[ItinerarySegment, ...]
    price: PriceSummary
    availability_status: AvailabilityStatus = AvailabilityStatus.NOT_CHECKED
    itinerary_id: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("itinerary must have at least one segment")
        # Segments must be sequential and chronological (PHASE.md property invariants).
        for i, seg in enumerate(self.segments, start=1):
            if seg.sequence != i:
                raise ValueError("segment sequences must be 1..n in order")
        for prev, nxt in zip(self.segments, self.segments[1:], strict=False):
            if nxt.flight.departure_at <= prev.flight.arrival_at:
                raise ValueError("connection departs before previous arrival")
            if nxt.flight.origin_code != prev.flight.destination_code:
                raise ValueError("segments do not form a connected path")
        if not self.itinerary_id:
            object.__setattr__(self, "itinerary_id", self._compute_id())

    @property
    def connection_count(self) -> int:
        return len(self.segments) - 1

    @property
    def departure_at(self) -> datetime:
        return self.segments[0].flight.departure_at

    @property
    def arrival_at(self) -> datetime:
        return self.segments[-1].flight.arrival_at

    @property
    def airborne_duration_minutes(self) -> int:
        return sum(seg.duration_minutes for seg in self.segments)

    @property
    def total_layover_minutes(self) -> int:
        total = 0
        for prev, nxt in zip(self.segments, self.segments[1:], strict=False):
            delta = nxt.flight.departure_at.astimezone(
                timezone.utc
            ) - prev.flight.arrival_at.astimezone(timezone.utc)
            total += int(delta.total_seconds() // 60)
        return total

    @property
    def total_duration_minutes(self) -> int:
        delta = self.arrival_at.astimezone(timezone.utc) - self.departure_at.astimezone(
            timezone.utc
        )
        return int(delta.total_seconds() // 60)

    def _compute_id(self) -> str:
        """SHA-256 over a canonical, locale-independent segment signature (PHASE.md §11).

        Uses UTC-normalized ISO instants and stable field ordering so equivalent
        itineraries hash identically across runs.
        """
        parts: list[str] = [self.segments[0].flight.operating_date.isoformat()]
        for seg in self.segments:
            f = seg.flight
            parts.append(
                "|".join(
                    [
                        f.carrier_code,
                        f.flight_number,
                        f.origin_code,
                        f.destination_code,
                        f.departure_at.astimezone(timezone.utc).isoformat(),
                        f.arrival_at.astimezone(timezone.utc).isoformat(),
                    ]
                )
            )
        canonical = "\n".join(parts)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"iti_{digest}"
