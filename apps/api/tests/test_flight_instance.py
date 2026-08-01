"""Unit tests for RTE-001 timezone-aware flight-instance resolution.

Covers PHASE.md §Flight Instances test list, §Effective-Date/Weekday handling, and
the DST rejection rule (ADR-003). Pure domain logic; no database required.
"""

from __future__ import annotations

import uuid
from datetime import date, time

import pytest

from app.db.models.airport import Airport
from app.db.models.scheduled_flight import ScheduledFlight
from app.domain.flight_instance import FlightInstance
from app.services.routing.instances import (
    ResolutionSkip,
    operates_on,
    resolve_instance,
)

SOURCE_ID = uuid.uuid4()

# --- synthetic SYNTHETIC TEST airports (not real Frontier inventory) ---
ATL = Airport(
    code="ATL",
    name="ATL",
    city="Atlanta",
    country_code="US",
    latitude=33.64,
    longitude=-84.43,
    timezone="America/New_York",
)
DEN = Airport(
    code="DEN",
    name="DEN",
    city="Denver",
    country_code="US",
    latitude=39.86,
    longitude=-104.67,
    timezone="America/Denver",
)
PHX = Airport(  # Arizona: no DST
    code="PHX",
    name="PHX",
    city="Phoenix",
    country_code="US",
    latitude=33.43,
    longitude=-112.01,
    timezone="America/Phoenix",
)
LAS = Airport(
    code="LAS",
    name="LAS",
    city="Las Vegas",
    country_code="US",
    latitude=36.08,
    longitude=-115.15,
    timezone="America/Los_Angeles",
)


def make_flight(
    *,
    origin="ATL",
    destination="DEN",
    dep=time(9, 35),
    arr=time(11, 5),
    arrival_day_offset=0,
    operating_days=None,
    effective_start=date(2026, 1, 1),
    effective_end=None,
    flight_number="1234",
) -> ScheduledFlight:
    return ScheduledFlight(
        id=uuid.uuid4(),
        carrier_code="F9",
        flight_number=flight_number,
        origin_code=origin,
        destination_code=destination,
        departure_local_time=dep,
        arrival_local_time=arr,
        arrival_day_offset=arrival_day_offset,
        effective_start=effective_start,
        effective_end=effective_end,
        operating_days=operating_days or [1, 2, 3, 4, 5, 6, 7],
        data_source_id=SOURCE_ID,
    )


def test_westbound_timezone_elapsed_duration():
    """ATL 09:35 EDT -> DEN 11:05 MDT: 90 clock minutes but 210 elapsed (TDD §13.2)."""
    flight = make_flight()
    inst = resolve_instance(flight, date(2026, 8, 4), ATL, DEN)
    assert isinstance(inst, FlightInstance)
    assert inst.duration_minutes == 210
    assert inst.departure_at.utcoffset().total_seconds() == -4 * 3600  # EDT
    assert inst.arrival_at.utcoffset().total_seconds() == -6 * 3600  # MDT


def test_eastbound_timezone():
    """DEN -> ATL eastbound: clock advances more than elapsed time."""
    flight = make_flight(origin="DEN", destination="ATL", dep=time(8, 0), arr=time(13, 30))
    inst = resolve_instance(flight, date(2026, 8, 4), DEN, ATL)
    assert isinstance(inst, FlightInstance)
    # 08:00 MDT -> 13:30 EDT = 5h30 clock, minus 2h tz = 3h30 elapsed
    assert inst.duration_minutes == 210


def test_same_timezone():
    # LAS and a second Pacific airport share America/Los_Angeles: clock == elapsed.
    sfo = Airport(
        code="SFO",
        name="SFO",
        city="San Francisco",
        country_code="US",
        latitude=37.62,
        longitude=-122.38,
        timezone="America/Los_Angeles",
    )
    flight = make_flight(origin="LAS", destination="SFO", dep=time(9, 0), arr=time(10, 30))
    inst = resolve_instance(flight, date(2026, 8, 4), LAS, sfo)
    assert isinstance(inst, FlightInstance)
    assert inst.duration_minutes == 90  # same tz, no offset difference


def test_arrival_day_offset_one():
    flight = make_flight(dep=time(23, 30), arr=time(1, 15), arrival_day_offset=1)
    inst = resolve_instance(flight, date(2026, 8, 4), ATL, DEN)
    assert isinstance(inst, FlightInstance)
    assert inst.arrival_at.date() == date(2026, 8, 5)
    assert inst.duration_minutes > 0


def test_arrival_day_offset_zero():
    inst = resolve_instance(make_flight(), date(2026, 8, 4), ATL, DEN)
    assert isinstance(inst, FlightInstance)
    assert inst.departure_at.date() == date(2026, 8, 4)
    assert inst.arrival_at.date() == date(2026, 8, 4)


def test_nonpositive_duration_rejected():
    # Arrival earlier than departure in absolute terms, same offset day.
    flight = make_flight(dep=time(12, 0), arr=time(10, 0), arrival_day_offset=0)
    result = resolve_instance(flight, date(2026, 8, 4), ATL, ATL)
    assert isinstance(result, ResolutionSkip)
    assert result.reason == "nonpositive_duration"


def test_invalid_timezone_rejected():
    bad = Airport(
        code="XXX",
        name="X",
        city="X",
        country_code="US",
        latitude=0.0,
        longitude=0.0,
        timezone="Not/AZone",
    )
    result = resolve_instance(make_flight(origin="XXX"), date(2026, 8, 4), bad, DEN)
    assert isinstance(result, ResolutionSkip)
    assert result.reason == "invalid_timezone"


# --- effective-date boundaries (PHASE.md §3) ---


def test_effective_start_boundary_inclusive():
    flight = make_flight(effective_start=date(2026, 8, 4), effective_end=date(2026, 8, 31))
    assert isinstance(resolve_instance(flight, date(2026, 8, 4), ATL, DEN), FlightInstance)


def test_day_before_effective_start_excluded():
    flight = make_flight(effective_start=date(2026, 8, 4))
    assert isinstance(resolve_instance(flight, date(2026, 8, 3), ATL, DEN), ResolutionSkip)


def test_effective_end_boundary_inclusive():
    flight = make_flight(effective_end=date(2026, 8, 31))
    assert isinstance(resolve_instance(flight, date(2026, 8, 31), ATL, DEN), FlightInstance)


def test_day_after_effective_end_excluded():
    flight = make_flight(effective_end=date(2026, 8, 31))
    assert isinstance(resolve_instance(flight, date(2026, 9, 1), ATL, DEN), ResolutionSkip)


def test_open_ended_schedule():
    flight = make_flight(effective_end=None)
    assert isinstance(resolve_instance(flight, date(2030, 1, 1), ATL, DEN), FlightInstance)


# --- weekday applicability (PHASE.md §4) ---


def test_weekday_applicable():
    # 2026-08-04 is a Tuesday (ISO 2).
    flight = make_flight(operating_days=[2])
    assert operates_on(flight, date(2026, 8, 4))
    assert isinstance(resolve_instance(flight, date(2026, 8, 4), ATL, DEN), FlightInstance)


def test_weekday_not_applicable():
    flight = make_flight(operating_days=[1, 3, 4, 5, 6, 7])  # no Tuesday
    assert not operates_on(flight, date(2026, 8, 4))
    assert isinstance(resolve_instance(flight, date(2026, 8, 4), ATL, DEN), ResolutionSkip)


# --- DST edge cases (PHASE.md §Daylight-Saving-Time Tests, ADR-003) ---


def test_spring_forward_nonexistent_departure_rejected():
    # US spring-forward 2026-03-08: 02:00->03:00 in America/New_York. 02:30 doesn't exist.
    flight = make_flight(dep=time(2, 30), arr=time(5, 0))
    result = resolve_instance(flight, date(2026, 3, 8), ATL, DEN)
    assert isinstance(result, ResolutionSkip)
    assert result.reason == "nonexistent_or_ambiguous_departure"


def test_fall_back_ambiguous_departure_rejected():
    # US fall-back 2026-11-01: 02:00->01:00 in America/New_York. 01:30 is ambiguous.
    flight = make_flight(dep=time(1, 30), arr=time(5, 0))
    result = resolve_instance(flight, date(2026, 11, 1), ATL, DEN)
    assert isinstance(result, ResolutionSkip)
    assert result.reason == "nonexistent_or_ambiguous_departure"


def test_non_dst_airport_unaffected_on_transition_day():
    # PHX (America/Phoenix) observes no DST; a normal time resolves fine on 2026-03-08.
    flight = make_flight(origin="PHX", destination="LAS", dep=time(2, 30), arr=time(3, 45))
    inst = resolve_instance(flight, date(2026, 3, 8), PHX, LAS)
    assert isinstance(inst, FlightInstance)


def test_deterministic_repeated_resolution():
    flight = make_flight()
    a = resolve_instance(flight, date(2026, 8, 4), ATL, DEN)
    b = resolve_instance(flight, date(2026, 8, 4), ATL, DEN)
    assert isinstance(a, FlightInstance) and isinstance(b, FlightInstance)
    assert a.departure_at == b.departure_at
    assert a.arrival_at == b.arrival_at
    assert a.duration_minutes == b.duration_minutes


def test_flight_instance_requires_aware_datetimes():
    from datetime import datetime

    with pytest.raises(ValueError):
        FlightInstance(
            scheduled_flight_id=uuid.uuid4(),
            carrier_code="F9",
            flight_number="1",
            origin_code="ATL",
            destination_code="DEN",
            departure_at=datetime(2026, 8, 4, 9, 35),  # naive
            arrival_at=datetime(2026, 8, 4, 11, 5),
            operating_date=date(2026, 8, 4),
            data_source_id=SOURCE_ID,
        )
