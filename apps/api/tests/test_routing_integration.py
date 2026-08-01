"""Phase 3 routing integration tests against PostgreSQL (PHASE.md §Integration Tests).

Exercises the full engine over persisted schedule data: active-version scoping,
version replacement, effective-date/weekday filtering, cross-midnight connections,
timezone-aware durations, dedup of duplicate DB rows, geographic filtering, sorting,
no-result, and invalid-origin handling. Uses SYNTHETIC TEST fixtures only.

Skipped automatically when the test database is SQLite (the active-source partial
unique index and SMALLINT[] arrays require PostgreSQL); runs in CI's postgres service.
"""

from __future__ import annotations

import os
from datetime import date, time

import pytest

from app.domain.errors import (
    DateOutsideScheduleRangeError,
    NoActiveScheduleError,
    UnknownOriginError,
)
from app.schemas.search import SearchCriteria
from app.services.routing.engine import search_itineraries
from tests.routing_fixtures import add_flight, make_source, seed_airports

_DB_URL = os.getenv("DATABASE_URL_TEST", os.getenv("DATABASE_URL", "sqlite:///:memory:"))
pytestmark = pytest.mark.skipif(
    "sqlite" in _DB_URL, reason="routing integration tests require PostgreSQL"
)

# 2026-08-04 is a Tuesday (ISO weekday 2).
TUESDAY = date(2026, 8, 4)


def _criteria(**kw) -> SearchCriteria:
    base = dict(origin="ATL", departure_date=TUESDAY)
    base.update(kw)
    return SearchCriteria(**base)


def test_no_active_schedule_raises(db_session):
    seed_airports(db_session)
    with pytest.raises(NoActiveScheduleError):
        search_itineraries(db_session, _criteria())


def test_direct_search_returns_results(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    add_flight(db_session, src, origin="ATL", destination="DEN", dep=time(9, 35), arr=time(11, 5))
    result = search_itineraries(db_session, _criteria(max_connections=0))
    assert result.active_source_version == "v1"
    assert len(result.itineraries) == 1
    it = result.itineraries[0]
    assert it.destination_code == "DEN"
    assert it.connection_count == 0
    assert it.total_duration_minutes == 210  # tz-aware ATL->DEN


def test_inactive_source_excluded_and_new_version_changes_results(db_session):
    seed_airports(db_session)
    old = make_source(db_session, version="v1", is_active=False)
    add_flight(db_session, old, origin="ATL", destination="MCO", dep=time(8, 0), arr=time(9, 30))
    new = make_source(db_session, version="v2", is_active=True)
    add_flight(db_session, new, origin="ATL", destination="DEN", dep=time(9, 35), arr=time(11, 5))

    result = search_itineraries(db_session, _criteria(max_connections=0))
    dests = {it.destination_code for it in result.itineraries}
    assert dests == {"DEN"}  # only the active v2 flight, never the inactive v1
    assert result.active_source_version == "v2"


def test_effective_date_filtering(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    # One flight covers Aug (so the active source's coverage includes TUESDAY), a
    # second flight only becomes effective in September. On TUESDAY only the first
    # should resolve -> effective-date filtering excludes the September flight.
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(9, 35),
        arr=time(11, 5),
        effective_start=date(2026, 8, 1),
        effective_end=date(2026, 12, 31),
        flight_number="1",
    )
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="MCO",
        dep=time(7, 0),
        arr=time(8, 0),
        effective_start=date(2026, 9, 1),
        effective_end=date(2026, 12, 31),
        flight_number="2",
    )
    result = search_itineraries(db_session, _criteria(max_connections=0))
    assert {it.destination_code for it in result.itineraries} == {"DEN"}


def test_weekday_filtering(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(9, 35),
        arr=time(11, 5),
        operating_days=[1, 3, 4, 5, 6, 7],  # no Tuesday
    )
    assert search_itineraries(db_session, _criteria(max_connections=0)).itineraries == []


def test_one_stop_same_day_connection(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    # ATL->DEN arrives 11:05 MT; DEN->LAS departs 12:30 MT (85 min layover).
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(9, 35),
        arr=time(11, 5),
        flight_number="1",
    )
    add_flight(
        db_session,
        src,
        origin="DEN",
        destination="LAS",
        dep=time(12, 30),
        arr=time(13, 45),
        flight_number="2",
    )
    result = search_itineraries(db_session, _criteria(max_connections=1))
    dests = {(it.destination_code, it.connection_count) for it in result.itineraries}
    assert ("DEN", 0) in dests  # direct first leg
    assert ("LAS", 1) in dests  # one-stop


def test_cross_midnight_connection(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    # First arrives late; second departs after midnight next local day.
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(21, 0),
        arr=time(22, 30),
        flight_number="1",
    )
    add_flight(
        db_session,
        src,
        origin="DEN",
        destination="LAS",
        dep=time(0, 30),
        arr=time(1, 45),
        arrival_day_offset=0,
        flight_number="2",
    )
    result = search_itineraries(db_session, _criteria(max_connections=1))
    one_stops = [it for it in result.itineraries if it.connection_count == 1]
    assert any(it.destination_code == "LAS" for it in one_stops)


def test_duplicate_db_rows_deduplicated(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    # Overlapping effective ranges produce two DB rows that resolve to the SAME
    # itinerary on TUESDAY (identical times/route/number, same operating date).
    # The unique constraint permits this because effective_start differs; the engine
    # must collapse them to one itinerary (PHASE.md §12, ADR-004).
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(9, 35),
        arr=time(11, 5),
        effective_start=date(2026, 8, 1),
        effective_end=date(2026, 12, 31),
        flight_number="1",
    )
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(9, 35),
        arr=time(11, 5),
        effective_start=date(2026, 8, 3),
        effective_end=date(2026, 12, 31),
        flight_number="1",
    )
    result = search_itineraries(db_session, _criteria(max_connections=0))
    assert len(result.itineraries) == 1


def test_domestic_and_international_filtering(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(9, 0),
        arr=time(10, 30),
        flight_number="1",
    )
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="CUN",
        dep=time(8, 0),
        arr=time(10, 0),
        flight_number="2",
    )

    dom = search_itineraries(db_session, _criteria(max_connections=0, domestic_only=True))
    assert {it.destination_code for it in dom.itineraries} == {"DEN"}

    intl = search_itineraries(db_session, _criteria(max_connections=0, international_only=True))
    assert {it.destination_code for it in intl.itineraries} == {"CUN"}


def test_sorting_by_destination(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="MCO",
        dep=time(9, 0),
        arr=time(10, 0),
        flight_number="1",
    )
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(9, 0),
        arr=time(10, 30),
        flight_number="2",
    )
    from app.domain.enums import SortMode

    result = search_itineraries(db_session, _criteria(max_connections=0, sort=SortMode.DESTINATION))
    dests = [it.destination_code for it in result.itineraries]
    assert dests == sorted(dests)


def test_no_result_search_is_not_error(db_session):
    seed_airports(db_session)
    make_source(db_session, version="v1", is_active=True)  # active source, no flights
    result = search_itineraries(db_session, _criteria(max_connections=1))
    assert result.itineraries == []


def test_unknown_origin_raises(db_session):
    seed_airports(db_session)
    make_source(db_session, version="v1", is_active=True)
    with pytest.raises(UnknownOriginError):
        search_itineraries(db_session, _criteria(origin="ZZZ"))


def test_date_outside_coverage_raises(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(9, 0),
        arr=time(10, 30),
        effective_start=date(2026, 8, 1),
        effective_end=date(2026, 8, 31),
    )
    with pytest.raises(DateOutsideScheduleRangeError):
        search_itineraries(db_session, _criteria(departure_date=date(2027, 1, 1)))


def test_deterministic_repeated_search(db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="DEN",
        dep=time(9, 35),
        arr=time(11, 5),
        flight_number="1",
    )
    add_flight(
        db_session,
        src,
        origin="ATL",
        destination="MCO",
        dep=time(7, 0),
        arr=time(8, 0),
        flight_number="2",
    )
    a = search_itineraries(db_session, _criteria(max_connections=0))
    b = search_itineraries(db_session, _criteria(max_connections=0))
    assert [it.itinerary_id for it in a.itineraries] == [it.itinerary_id for it in b.itineraries]
