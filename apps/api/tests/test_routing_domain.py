"""Unit tests for itinerary domain, connection validation, dedup, and pricing.

Covers PHASE.md test lists for Direct Itineraries, One-Stop Itineraries, Duration
Calculations, Deduplication, and Pricing. Pure domain logic; no database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.domain.enums import AvailabilityStatus, PriceStatus
from app.domain.flight_instance import FlightInstance
from app.domain.itinerary import Itinerary, ItinerarySegment, PriceSummary
from app.services.routing.connections import ConnectionPolicy, validate_connection
from app.services.routing.dedup import deduplicate
from app.services.routing.pricing import PriceEstimator

ET = ZoneInfo("America/New_York")
MT = ZoneInfo("America/Denver")
PT = ZoneInfo("America/Los_Angeles")
SOURCE = uuid.uuid4()
POLICY = ConnectionPolicy(45, 240, 720)
ESTIMATOR = PriceEstimator(Decimal("14.91"), international_estimation_enabled=False)


def inst(origin, dest, dep, arr, *, tz_dep=ET, tz_arr=MT, fnum="1", fid=None) -> FlightInstance:
    return FlightInstance(
        scheduled_flight_id=fid or uuid.uuid4(),
        carrier_code="F9",
        flight_number=fnum,
        origin_code=origin,
        destination_code=dest,
        departure_at=dep.replace(tzinfo=tz_dep),
        arrival_at=arr.replace(tzinfo=tz_arr),
        operating_date=dep.date(),
        data_source_id=SOURCE,
    )


def direct(f: FlightInstance) -> Itinerary:
    return Itinerary(
        origin_code=f.origin_code,
        destination_code=f.destination_code,
        segments=(ItinerarySegment(1, f),),
        price=ESTIMATOR.estimate(1, is_international=False),
    )


# --- direct itineraries (PHASE.md §5) ---


def test_direct_itinerary_shape():
    f = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 35), datetime(2026, 8, 4, 11, 5))
    it = direct(f)
    assert it.connection_count == 0
    assert it.total_layover_minutes == 0
    assert it.airborne_duration_minutes == 210
    assert it.total_duration_minutes == 210
    assert it.availability_status == AvailabilityStatus.NOT_CHECKED
    assert it.itinerary_id.startswith("iti_")


def test_deterministic_itinerary_id_stable():
    f = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 35), datetime(2026, 8, 4, 11, 5), fid=SOURCE)
    assert direct(f).itinerary_id == direct(f).itinerary_id


def test_different_departure_times_distinct_ids():
    f1 = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 35), datetime(2026, 8, 4, 11, 5))
    f2 = inst("ATL", "DEN", datetime(2026, 8, 4, 14, 0), datetime(2026, 8, 4, 15, 30))
    assert direct(f1).itinerary_id != direct(f2).itinerary_id


# --- one-stop duration invariant (PHASE.md §10) ---


def test_total_duration_equals_airborne_plus_layover():
    first = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 0), datetime(2026, 8, 4, 10, 30))
    second = inst(
        "DEN",
        "LAS",
        datetime(2026, 8, 4, 12, 0),
        datetime(2026, 8, 4, 13, 0),
        tz_dep=MT,
        tz_arr=PT,
        fnum="2",
    )
    it = Itinerary(
        origin_code="ATL",
        destination_code="LAS",
        segments=(ItinerarySegment(1, first), ItinerarySegment(2, second)),
        price=ESTIMATOR.estimate(2, is_international=False),
    )
    assert it.connection_count == 1
    assert it.total_duration_minutes == it.airborne_duration_minutes + it.total_layover_minutes


def test_itinerary_rejects_chronology_violation():
    first = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 0), datetime(2026, 8, 4, 12, 0))
    second = inst(
        "DEN",
        "LAS",
        datetime(2026, 8, 4, 11, 0),
        datetime(2026, 8, 4, 12, 30),
        tz_dep=MT,
        tz_arr=PT,
    )
    with pytest.raises(ValueError):
        Itinerary(
            origin_code="ATL",
            destination_code="LAS",
            segments=(ItinerarySegment(1, first), ItinerarySegment(2, second)),
            price=ESTIMATOR.estimate(2, is_international=False),
        )


# --- connection validation (PHASE.md §8) ---


def _pair(layover_min: int):
    first = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 0), datetime(2026, 8, 4, 10, 30))
    # first arrives 10:30 MT. second departs layover_min later, same tz, 1h flight.
    dep = datetime(2026, 8, 4, 10, 30) + timedelta(minutes=layover_min)
    arr = dep + timedelta(hours=1)
    second = inst("DEN", "LAS", dep, arr, tz_dep=MT, tz_arr=PT, fnum="2")
    return first, second


def test_connection_at_min_boundary_valid():
    first, second = _pair(45)
    assert validate_connection(first, second, "ATL", POLICY).is_valid


def test_connection_below_min_rejected():
    first, second = _pair(44)
    r = validate_connection(first, second, "ATL", POLICY)
    assert not r.is_valid and r.reason == "below_min_connection"


def test_connection_at_max_boundary_valid():
    first, second = _pair(240)
    assert validate_connection(first, second, "ATL", POLICY).is_valid


def test_connection_above_max_rejected():
    first, second = _pair(241)
    r = validate_connection(first, second, "ATL", POLICY)
    assert not r.is_valid and r.reason == "above_max_connection"


def test_return_to_origin_rejected():
    first = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 0), datetime(2026, 8, 4, 10, 30))
    second = inst(
        "DEN", "ATL", datetime(2026, 8, 4, 12, 0), datetime(2026, 8, 4, 15, 0), tz_dep=MT, tz_arr=ET
    )
    r = validate_connection(first, second, "ATL", POLICY)
    assert not r.is_valid and r.reason in {"return_to_origin", "repeated_airport"}


def test_repeated_airport_rejected():
    first = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 0), datetime(2026, 8, 4, 10, 30))
    second = inst(
        "DEN", "DEN", datetime(2026, 8, 4, 12, 0), datetime(2026, 8, 4, 13, 0), tz_dep=MT, tz_arr=MT
    )
    r = validate_connection(first, second, "ATL", POLICY)
    assert not r.is_valid and r.reason == "repeated_airport"


def test_second_before_first_rejected():
    first = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 0), datetime(2026, 8, 4, 15, 0))
    second = inst(
        "DEN", "LAS", datetime(2026, 8, 4, 12, 0), datetime(2026, 8, 4, 13, 0), tz_dep=MT, tz_arr=PT
    )
    r = validate_connection(first, second, "ATL", POLICY)
    assert not r.is_valid and r.reason == "nonpositive_layover"


def test_total_duration_exceeded_rejected():
    tight = ConnectionPolicy(45, 600, 120)  # max total 2h
    first, second = _pair(60)
    r = validate_connection(first, second, "ATL", tight)
    assert not r.is_valid and r.reason == "above_max_total_duration"


# --- deduplication (PHASE.md §12, ADR-004) ---


def test_exact_duplicate_collapsed():
    f = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 35), datetime(2026, 8, 4, 11, 5), fid=SOURCE)
    out = deduplicate([direct(f), direct(f)])
    assert len(out) == 1


def test_distinct_itineraries_preserved():
    f1 = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 35), datetime(2026, 8, 4, 11, 5))
    f2 = inst("ATL", "LAS", datetime(2026, 8, 4, 9, 35), datetime(2026, 8, 4, 11, 5), tz_arr=PT)
    out = deduplicate([direct(f1), direct(f2)])
    assert len(out) == 2


def test_dedup_idempotent():
    f = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 35), datetime(2026, 8, 4, 11, 5), fid=SOURCE)
    once = deduplicate([direct(f), direct(f)])
    assert deduplicate(once) == once


def test_dedup_stable_winner_by_flight_id():
    # Same identity (same times/codes/flight numbers) but different scheduled_flight_id.
    low = uuid.UUID(int=1)
    high = uuid.UUID(int=2)
    fa = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 35), datetime(2026, 8, 4, 11, 5), fid=high)
    fb = inst("ATL", "DEN", datetime(2026, 8, 4, 9, 35), datetime(2026, 8, 4, 11, 5), fid=low)
    out = deduplicate([direct(fa), direct(fb)])
    assert len(out) == 1
    assert out[0].segments[0].flight.scheduled_flight_id == low


# --- pricing (PHASE.md §15) ---


def test_one_segment_estimate():
    p = ESTIMATOR.estimate(1, is_international=False)
    assert p.amount == Decimal("14.91")
    assert p.status == PriceStatus.ESTIMATED
    assert p.verified_at is None
    assert p.disclaimer


def test_two_segment_estimate():
    p = ESTIMATOR.estimate(2, is_international=False)
    assert p.amount == Decimal("29.82")
    assert p.segment_count == 2


def test_decimal_precision_no_float():
    p = ESTIMATOR.estimate(3, is_international=False)
    assert isinstance(p.amount, Decimal)
    assert p.amount == Decimal("44.73")


def test_international_disabled_is_unknown_not_zero():
    p = ESTIMATOR.estimate(1, is_international=True)
    assert p.amount is None
    assert p.status == PriceStatus.UNKNOWN


def test_international_enabled_estimates():
    est = PriceEstimator(Decimal("14.91"), international_estimation_enabled=True)
    p = est.estimate(1, is_international=True)
    assert p.amount == Decimal("14.91")
    assert p.status == PriceStatus.ESTIMATED


def test_estimated_price_cannot_carry_verified_at():
    with pytest.raises(ValueError):
        PriceSummary(
            currency="USD",
            segment_count=1,
            status=PriceStatus.ESTIMATED,
            amount=Decimal("14.91"),
            verified_at=datetime.now(timezone.utc),
        )
