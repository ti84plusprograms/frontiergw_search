"""API-002 search endpoint — full serialization against PostgreSQL.

Requires PostgreSQL (SMALLINT[] operating_days + one-active-source partial index),
mirroring test_routing_integration. Skipped on SQLite.
"""

from __future__ import annotations

import os
from datetime import time

import pytest

from tests.routing_fixtures import add_flight, make_source, seed_airports

_DB_URL = os.getenv("DATABASE_URL_TEST", os.getenv("DATABASE_URL", "sqlite:///:memory:"))
pytestmark = pytest.mark.skipif(
    "sqlite" in _DB_URL, reason="search integration tests require PostgreSQL"
)

DIRECT = {"origin": "ATL", "departure_date": "2026-08-04", "max_connections": 0, "sort": "PRICE"}


def test_direct_search_serialization(client, db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="2026-08-01", is_active=True)
    add_flight(db_session, src, origin="ATL", destination="DEN", dep=time(9, 35), arr=time(11, 5))

    resp = client.post("/api/v1/search", json=DIRECT)
    assert resp.status_code == 200
    body = resp.json()

    assert body["result_count"] == 1
    assert body["search_id"].startswith("srch_")
    # routing_fixtures uses synthetic city == code; timezone is the real IANA zone.
    assert body["origin"]["code"] == "ATL"
    assert body["origin"]["timezone"] == "America/New_York"

    it = body["results"][0]
    assert it["destination"]["code"] == "DEN"
    assert it["connection_count"] == 0
    assert it["total_duration_minutes"] == 210
    # Timezone offsets preserved in ISO datetimes.
    assert it["departure_at"].endswith("-04:00")  # ATL EDT
    assert it["arrival_at"].endswith("-06:00")  # DEN MDT
    # Money is a decimal string, never a float.
    assert it["price"]["amount"] == "14.91"
    assert it["price"]["status"] == "ESTIMATED"
    assert it["price"]["verified_at"] is None
    assert isinstance(it["price"]["amount"], str)
    # Availability never checked in Phase 4.
    assert it["availability"] == {
        "status": "NOT_CHECKED",
        "checked_at": None,
        "source": None,
        "confidence": "LOW",
    }
    assert it["booking_url"] is None

    # Freshness + always-present availability warning.
    assert body["data_freshness"]["schedule_version"] == "2026-08-01"
    codes = {w["code"] for w in body["warnings"]}
    assert "AVAILABILITY_NOT_CHECKED" in codes


def test_no_result_is_200_with_warning(client, db_session):
    seed_airports(db_session)
    make_source(db_session, version="v1", is_active=True)  # active source, no flights
    resp = client.post("/api/v1/search", json=DIRECT)
    assert resp.status_code == 200
    body = resp.json()
    assert body["result_count"] == 0
    assert body["results"] == []
    codes = {w["code"] for w in body["warnings"]}
    assert "NO_MATCHING_ITINERARIES" in codes


def test_one_stop_search_serialization(client, db_session):
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
        origin="DEN",
        destination="LAS",
        dep=time(12, 30),
        arr=time(13, 45),
        flight_number="2",
    )

    resp = client.post(
        "/api/v1/search",
        json={"origin": "ATL", "departure_date": "2026-08-04", "max_connections": 1},
    )
    assert resp.status_code == 200
    one_stops = [it for it in resp.json()["results"] if it["connection_count"] == 1]
    assert one_stops
    it = one_stops[0]
    assert it["destination"]["code"] == "LAS"
    assert len(it["segments"]) == 2
    assert it["segments"][0]["sequence"] == 1
    assert it["segments"][1]["sequence"] == 2
    assert it["price"]["amount"] == "29.82"  # 2 segments


def test_date_outside_coverage_is_422(client, db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="v1", is_active=True)
    add_flight(db_session, src, origin="ATL", destination="DEN", dep=time(9, 0), arr=time(10, 30))
    resp = client.post(
        "/api/v1/search",
        json={"origin": "ATL", "departure_date": "2030-01-01", "max_connections": 0},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "DATE_OUTSIDE_SCHEDULE_RANGE"


def test_status_and_search_use_same_source(client, db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="2026-08-01", is_active=True)
    add_flight(db_session, src, origin="ATL", destination="DEN", dep=time(9, 0), arr=time(10, 30))

    status = client.get("/api/v1/schedules/status").json()
    search = client.post("/api/v1/search", json=DIRECT).json()
    assert search["data_freshness"]["schedule_version"] == status["version"]
    assert status["active"] is True
