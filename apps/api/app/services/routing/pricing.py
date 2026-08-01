"""Estimated GoWild pricing (RTE-007).

PHASE.md §15–§16: exact decimal arithmetic, per-segment estimate, ESTIMATED status,
no verified timestamp, international estimation disabled unless configured. Unknown
estimates are represented by ``amount=None`` with status UNKNOWN, never zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import PriceStatus
from app.domain.itinerary import PriceSummary


@dataclass(frozen=True, slots=True)
class PriceEstimator:
    domestic_segment_price: Decimal
    international_estimation_enabled: bool
    currency: str = "USD"

    def estimate(self, segment_count: int, *, is_international: bool) -> PriceSummary:
        if segment_count < 1:
            raise ValueError("segment_count must be >= 1")
        if is_international and not self.international_estimation_enabled:
            # Explicit unknown state, not zero (PHASE.md §15).
            return PriceSummary(
                currency=self.currency,
                segment_count=segment_count,
                status=PriceStatus.UNKNOWN,
                amount=None,
            )
        amount = self.domestic_segment_price * segment_count
        return PriceSummary(
            currency=self.currency,
            segment_count=segment_count,
            status=PriceStatus.ESTIMATED,
            amount=amount,
        )
