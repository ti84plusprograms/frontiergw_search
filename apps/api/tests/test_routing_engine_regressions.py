"""Regression tests for adversarial routing-engine cases."""

from datetime import date, time

from app.db.models.airport import Airport
from app.schemas.search import SearchCriteria
from app.services.routing.engine import search_itineraries
from tests.routing_fixtures import add_flight, make_source, seed_airports


def _criteria(**overrides) -> SearchCriteria:
    values = {"origin": "ATL", "departure_date": date(2026, 8, 4), "max_connections": 1}
    values.update(overrides)
    return SearchCriteria(**values)


def test_next_day_effective_second_segment_is_discovered(db_session):
    seed_airports(db_session)
    source = make_source(db_session, version="next-day-v1", is_active=True)
    add_flight(
        db_session,
        source,
        origin="ATL",
        destination="DEN",
        dep=time(21, 0),
        arr=time(22, 30),
        flight_number="1",
    )
    add_flight(
        db_session,
        source,
        origin="DEN",
        destination="LAS",
        dep=time(0, 30),
        arr=time(1, 45),
        effective_start=date(2026, 8, 5),
        effective_end=date(2026, 8, 31),
        flight_number="2",
    )

    result = search_itineraries(db_session, _criteria())

    assert any(
        itinerary.destination_code == "LAS" and itinerary.connection_count == 1
        for itinerary in result.itineraries
    )


def test_resolution_skip_reason_is_reported_in_search_diagnostics(db_session):
    seed_airports(db_session)
    db_session.query(Airport).filter_by(code="DEN").one().timezone = "Invalid/Zone"
    source = make_source(db_session, version="invalid-destination-timezone", is_active=True)
    add_flight(
        db_session,
        source,
        origin="ATL",
        destination="DEN",
        dep=time(9, 0),
        arr=time(11, 0),
    )

    result = search_itineraries(db_session, _criteria(max_connections=0))

    assert result.itineraries == []
    assert result.diagnostics["resolution_skipped"] == 1
    assert result.diagnostics["resolution_skip_invalid_timezone"] == 1
