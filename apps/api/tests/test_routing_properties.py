"""Property-based routing invariants (PHASE.md §Property-Based Tests).

These exercise the pure domain layer (itinerary construction, dedup, sorting, pricing)
with generated inputs. No database or network access.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from hypothesis import assume, given
from hypothesis import strategies as st

from app.domain.enums import SortMode
from app.domain.flight_instance import FlightInstance
from app.domain.itinerary import Itinerary, ItinerarySegment
from app.services.routing.dedup import deduplicate
from app.services.routing.pricing import PriceEstimator
from app.services.routing.sorting import sort_itineraries

UTC = timezone.utc
EST = PriceEstimator(Decimal("14.91"), international_estimation_enabled=False)

_CODES = ["ATL", "DEN", "LAS", "MCO", "PHX", "ORL", "CUN"]


def _flight(origin, dest, dep_minute, dur_minutes, fnum="1", fid=None):
    dep = datetime(2026, 8, 4, 0, 0, tzinfo=UTC) + timedelta(minutes=dep_minute)
    arr = dep + timedelta(minutes=dur_minutes)
    return FlightInstance(
        scheduled_flight_id=fid or uuid.uuid4(),
        carrier_code="F9",
        flight_number=fnum,
        origin_code=origin,
        destination_code=dest,
        departure_at=dep,
        arrival_at=arr,
        operating_date=date(2026, 8, 4),
        data_source_id=uuid.uuid4(),
    )


@st.composite
def direct_itineraries(draw):
    origin, dest = draw(st.sampled_from(_CODES)), draw(st.sampled_from(_CODES))
    assume(origin != dest)
    dep = draw(st.integers(min_value=0, max_value=1400))
    dur = draw(st.integers(min_value=30, max_value=600))
    f = _flight(origin, dest, dep, dur)
    return Itinerary(
        origin_code=origin,
        destination_code=dest,
        segments=(ItinerarySegment(1, f),),
        price=EST.estimate(1, is_international=False),
    )


@st.composite
def one_stop_itineraries(draw):
    origin, mid, dest = (
        draw(st.sampled_from(_CODES)),
        draw(st.sampled_from(_CODES)),
        draw(st.sampled_from(_CODES)),
    )
    assume(len({origin, mid, dest}) == 3)
    dep1 = draw(st.integers(min_value=0, max_value=600))
    dur1 = draw(st.integers(min_value=30, max_value=300))
    layover = draw(st.integers(min_value=45, max_value=240))
    dur2 = draw(st.integers(min_value=30, max_value=300))
    first = _flight(origin, mid, dep1, dur1, fnum="1")
    second = _flight(mid, dest, dep1 + dur1 + layover, dur2, fnum="2")
    return Itinerary(
        origin_code=origin,
        destination_code=dest,
        segments=(ItinerarySegment(1, first), ItinerarySegment(2, second)),
        price=EST.estimate(2, is_international=False),
    )


@given(st.one_of(direct_itineraries(), one_stop_itineraries()))
def test_segment_count_one_or_two(it):
    assert 1 <= len(it.segments) <= 2


@given(st.one_of(direct_itineraries(), one_stop_itineraries()))
def test_connection_count_equals_segments_minus_one(it):
    assert it.connection_count == len(it.segments) - 1


@given(st.one_of(direct_itineraries(), one_stop_itineraries()))
def test_segments_chronological_and_positive(it):
    for seg in it.segments:
        assert seg.flight.arrival_at > seg.flight.departure_at
    for i in range(len(it.segments) - 1):
        assert it.segments[i + 1].flight.departure_at > it.segments[i].flight.arrival_at


@given(one_stop_itineraries())
def test_no_airport_repeats(it):
    path = [it.segments[0].flight.origin_code] + [s.flight.destination_code for s in it.segments]
    assert len(set(path)) == len(path)


@given(st.one_of(direct_itineraries(), one_stop_itineraries()))
def test_final_destination_differs_from_origin(it):
    assert it.destination_code != it.origin_code


@given(st.one_of(direct_itineraries(), one_stop_itineraries()))
def test_total_duration_positive(it):
    assert it.total_duration_minutes > 0


@given(st.one_of(direct_itineraries(), one_stop_itineraries()))
def test_total_equals_airborne_plus_layover(it):
    assert it.total_duration_minutes == it.airborne_duration_minutes + it.total_layover_minutes


@given(st.integers(min_value=1, max_value=2))
def test_price_monotonic_in_segments(segment_count):
    one = EST.estimate(1, is_international=False).amount
    two = EST.estimate(2, is_international=False).amount
    assert one is not None and two is not None and two > one


@given(direct_itineraries())
def test_equivalent_inputs_produce_identical_ids(it):
    # Rebuild an identical itinerary; IDs must match (deterministic identity).
    same = Itinerary(
        origin_code=it.origin_code,
        destination_code=it.destination_code,
        segments=it.segments,
        price=it.price,
    )
    assert same.itinerary_id == it.itinerary_id


@given(st.lists(direct_itineraries(), max_size=8))
def test_dedup_idempotent(items):
    once = deduplicate(items)
    assert deduplicate(once) == once


@given(st.lists(direct_itineraries(), max_size=8), st.sampled_from(list(SortMode)))
def test_sorting_deterministic(items, mode):
    assert sort_itineraries(items, mode) == sort_itineraries(list(items), mode)
