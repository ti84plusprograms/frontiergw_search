"""Unit tests for SearchCriteria validation, filters, and sorting (RTE-006)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.db.models.airport import Airport
from app.domain.enums import SortMode
from app.domain.flight_instance import FlightInstance
from app.domain.itinerary import Itinerary, ItinerarySegment
from app.schemas.search import SearchCriteria
from app.services.routing.filters import apply_filters, matches
from app.services.routing.pricing import PriceEstimator
from app.services.routing.sorting import sort_itineraries

ET = ZoneInfo("America/New_York")
MT = ZoneInfo("America/Denver")
EST = PriceEstimator(Decimal("14.91"), international_estimation_enabled=False)

AIRPORTS = {
    "ATL": Airport(
        code="ATL",
        name="ATL",
        city="Atlanta",
        country_code="US",
        latitude=1.0,
        longitude=1.0,
        timezone="America/New_York",
    ),
    "DEN": Airport(
        code="DEN",
        name="DEN",
        city="Denver",
        country_code="US",
        latitude=1.0,
        longitude=1.0,
        timezone="America/Denver",
    ),
    "CUN": Airport(
        code="CUN",
        name="CUN",
        city="Cancun",
        country_code="MX",
        latitude=1.0,
        longitude=1.0,
        timezone="America/Cancun",
    ),
}


def direct_it(dest, dep_h, dur_min=210, dep_min=0):
    dep = datetime(2026, 8, 4, dep_h, dep_min, tzinfo=ET)
    arr = datetime(2026, 8, 4, dep_h, dep_min, tzinfo=MT)  # +2h absolute at these tz
    f = FlightInstance(
        scheduled_flight_id=uuid.uuid4(),
        carrier_code="F9",
        flight_number="1",
        origin_code="ATL",
        destination_code=dest,
        departure_at=dep,
        arrival_at=arr,
        operating_date=date(2026, 8, 4),
        data_source_id=uuid.uuid4(),
    )
    return Itinerary(
        origin_code="ATL",
        destination_code=dest,
        segments=(ItinerarySegment(1, f),),
        price=EST.estimate(1, is_international=(dest == "CUN")),
    )


# --- SearchCriteria validation ---


def test_origin_normalized_uppercase():
    c = SearchCriteria(origin="atl", departure_date=date(2026, 8, 4))
    assert c.origin == "ATL"


def test_invalid_origin_rejected():
    with pytest.raises(ValidationError):
        SearchCriteria(origin="AT", departure_date=date(2026, 8, 4))


def test_max_connections_bounded():
    with pytest.raises(ValidationError):
        SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4), max_connections=2)


def test_connection_range_validated():
    with pytest.raises(ValidationError):
        SearchCriteria(
            origin="ATL",
            departure_date=date(2026, 8, 4),
            min_connection_minutes=200,
            max_connection_minutes=100,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("min_connection_minutes", 19),
        ("min_connection_minutes", 361),
        ("max_connection_minutes", 19),
        ("max_connection_minutes", 361),
        ("max_total_duration_minutes", 59),
        ("max_total_duration_minutes", 1441),
    ],
)
def test_numeric_criteria_bounds(field, value):
    with pytest.raises(ValidationError):
        SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4), **{field: value})


def test_geographic_conflict_rejected():
    with pytest.raises(ValidationError):
        SearchCriteria(
            origin="ATL",
            departure_date=date(2026, 8, 4),
            domestic_only=True,
            international_only=True,
        )


def test_negative_price_rejected():
    with pytest.raises(ValidationError):
        SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4), max_price=-1)


# --- filters ---


def test_depart_after_boundary():
    it = direct_it("DEN", 9)  # departs 09:00 local
    c = SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4), depart_after=time(9, 0))
    assert matches(it, c, AIRPORTS)  # inclusive boundary
    c2 = SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4), depart_after=time(9, 1))
    assert not matches(it, c2, AIRPORTS)


def test_max_price_filter():
    it = direct_it("DEN", 9)  # $14.91
    ok = SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4), max_price=15)
    no = SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4), max_price=10)
    assert matches(it, ok, AIRPORTS)
    assert not matches(it, no, AIRPORTS)


def test_domestic_only():
    dom = direct_it("DEN", 9)
    intl = direct_it("CUN", 9)
    c = SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4), domestic_only=True)
    out = apply_filters([dom, intl], c, AIRPORTS)
    assert out == [dom]


def test_international_only():
    dom = direct_it("DEN", 9)
    intl = direct_it("CUN", 9)
    c = SearchCriteria(origin="ATL", departure_date=date(2026, 8, 4), international_only=True)
    out = apply_filters([dom, intl], c, AIRPORTS)
    assert out == [intl]


# --- sorting ---


def test_sort_by_price_unknown_last():
    dom = direct_it("DEN", 9)  # $14.91
    intl = direct_it("CUN", 8)  # UNKNOWN price (intl disabled)
    out = sort_itineraries([intl, dom], SortMode.PRICE)
    assert out[0] == dom and out[1] == intl


def test_sort_earliest_departure():
    early = direct_it("DEN", 7)
    late = direct_it("DEN", 15, dep_min=30)
    out = sort_itineraries([late, early], SortMode.EARLIEST_DEPARTURE)
    assert out[0] == early


def test_sort_latest_departure():
    early = direct_it("DEN", 7)
    late = direct_it("DEN", 15, dep_min=30)
    out = sort_itineraries([early, late], SortMode.LATEST_DEPARTURE)
    assert out[0] == late


def test_sort_destination_alphabetical():
    a = direct_it("DEN", 9)
    b = direct_it("CUN", 9)
    out = sort_itineraries([a, b], SortMode.DESTINATION)
    assert out[0].destination_code == "CUN"


def test_sort_deterministic_repeatable():
    items = [direct_it("DEN", 9), direct_it("CUN", 8), direct_it("DEN", 7)]
    assert sort_itineraries(items, SortMode.PRICE) == sort_itineraries(items, SortMode.PRICE)
