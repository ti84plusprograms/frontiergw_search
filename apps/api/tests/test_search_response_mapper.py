"""Unit tests for the search response mapper (ADR-006/007/008). No database."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.db.models.airport import Airport
from app.domain.enums import PriceStatus
from app.domain.flight_instance import FlightInstance
from app.domain.itinerary import Itinerary, ItinerarySegment, PriceSummary
from app.services.search_response import build_search_response

ET = ZoneInfo("America/New_York")
MT = ZoneInfo("America/Denver")

ATL = Airport(
    code="ATL",
    name="ATL",
    city="Atlanta",
    country_code="US",
    latitude=1.0,
    longitude=1.0,
    timezone="America/New_York",
)
DEN = Airport(
    code="DEN",
    name="DEN",
    city="Denver",
    country_code="US",
    latitude=1.0,
    longitude=1.0,
    timezone="America/Denver",
)
AIRPORTS = {"ATL": ATL, "DEN": DEN}
STATUS = {
    "source": "syn",
    "version": "2026-08-01",
    "retrieved_at": datetime(2026, 8, 1, tzinfo=ET),
    "effective_start": date(2026, 8, 1),
    "effective_end": date(2026, 10, 31),
    "route_count": 1,
    "scheduled_flight_count": 1,
}


def _itin(amount: Decimal | None = Decimal("14.91"), status=PriceStatus.ESTIMATED):
    f = FlightInstance(
        scheduled_flight_id=uuid.uuid4(),
        carrier_code="F9",
        flight_number="1",
        origin_code="ATL",
        destination_code="DEN",
        departure_at=datetime(2026, 8, 4, 9, 35, tzinfo=ET),
        arrival_at=datetime(2026, 8, 4, 11, 5, tzinfo=MT),
        operating_date=date(2026, 8, 4),
        data_source_id=uuid.uuid4(),
    )
    return Itinerary(
        origin_code="ATL",
        destination_code="DEN",
        segments=(ItinerarySegment(1, f),),
        price=PriceSummary(currency="USD", segment_count=1, status=status, amount=amount),
    )


def _build(itins, max_results=250):
    return build_search_response(
        origin_airport=ATL,
        departure_date=date(2026, 8, 4),
        itineraries=itins,
        airports=AIRPORTS,
        schedule_status=STATUS,
        max_results=max_results,
    )


def test_money_serialized_as_string():
    resp = _build([_itin()])
    assert resp.results[0].price.amount == "14.91"
    assert isinstance(resp.results[0].price.amount, str)


def test_unknown_price_serialized_as_none():
    resp = _build([_itin(amount=None, status=PriceStatus.UNKNOWN)])
    assert resp.results[0].price.amount is None


def test_offsets_preserved():
    resp = _build([_itin()])
    seg = resp.results[0].segments[0]
    assert seg.departure_at.utcoffset().total_seconds() == -4 * 3600
    assert seg.arrival_at.utcoffset().total_seconds() == -6 * 3600


def test_availability_always_not_checked():
    resp = _build([_itin()])
    av = resp.results[0].availability
    assert av.status.value == "NOT_CHECKED"
    assert av.confidence == "LOW"
    assert av.checked_at is None


def test_availability_warning_always_present():
    resp = _build([_itin()])
    assert any(w.code.value == "AVAILABILITY_NOT_CHECKED" for w in resp.warnings)


def test_no_result_warning():
    resp = _build([])
    assert resp.result_count == 0
    assert any(w.code.value == "NO_MATCHING_ITINERARIES" for w in resp.warnings)


def test_truncation_warning_and_cap():
    resp = _build([_itin() for _ in range(5)], max_results=2)
    assert resp.result_count == 2
    assert any(w.code.value == "RESULTS_TRUNCATED" for w in resp.warnings)


def test_freshness_populated():
    resp = _build([_itin()])
    assert resp.data_freshness.schedule_version == "2026-08-01"
    assert resp.data_freshness.schedule_effective_end == date(2026, 10, 31)
    assert resp.data_freshness.availability_checked_at is None
