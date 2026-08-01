"""API-002 search endpoint — error/validation paths (SQLite-safe, no routing needed)."""

from __future__ import annotations

from datetime import time

import pytest

from tests.routing_fixtures import add_flight, make_source, seed_airports

VALID = {"origin": "ATL", "departure_date": "2026-08-04", "max_connections": 0}


def _active_schedule(db):
    seed_airports(db)
    src = make_source(db, version="v1", is_active=True)
    add_flight(db, src, origin="ATL", destination="DEN", dep=time(9, 0), arr=time(10, 30))


def test_no_active_schedule_is_503(client, db_session):
    seed_airports(db_session)
    resp = client.post("/api/v1/search", json=VALID)
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "NO_ACTIVE_SCHEDULE"
    assert resp.headers["X-Request-ID"]


def test_unknown_origin_is_422_invalid_airport(client, db_session):
    _active_schedule(db_session)
    resp = client.post("/api/v1/search", json={**VALID, "origin": "ZZZ"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_AIRPORT"


def test_bad_origin_format_is_422(client, db_session):
    _active_schedule(db_session)
    resp = client.post("/api/v1/search", json={**VALID, "origin": "AT"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_REQUEST"


def test_conflicting_geo_filters_is_422(client, db_session):
    _active_schedule(db_session)
    resp = client.post(
        "/api/v1/search", json={**VALID, "domestic_only": True, "international_only": True}
    )
    assert resp.status_code == 422


def test_unknown_field_rejected(client, db_session):
    _active_schedule(db_session)
    resp = client.post("/api/v1/search", json={**VALID, "bogus": 1})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_REQUEST"


def test_invalid_connection_range_is_422(client, db_session):
    _active_schedule(db_session)
    resp = client.post(
        "/api/v1/search",
        json={**VALID, "min_connection_minutes": 200, "max_connection_minutes": 100},
    )
    assert resp.status_code == 422


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
def test_bounded_search_values_are_422_before_routing(client, db_session, field, value):
    resp = client.post("/api/v1/search", json={**VALID, field: value})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_REQUEST"


def test_bad_date_format_is_422(client, db_session):
    _active_schedule(db_session)
    resp = client.post("/api/v1/search", json={**VALID, "departure_date": "not-a-date"})
    assert resp.status_code == 422


def test_unsupported_sort_is_422(client, db_session):
    _active_schedule(db_session)
    resp = client.post("/api/v1/search", json={**VALID, "sort": "CHEAPEST"})
    assert resp.status_code == 422


def test_max_connections_out_of_range_is_422(client, db_session):
    _active_schedule(db_session)
    resp = client.post("/api/v1/search", json={**VALID, "max_connections": 2})
    assert resp.status_code == 422


def test_error_body_has_no_internal_leakage(client, db_session):
    seed_airports(db_session)
    resp = client.post("/api/v1/search", json=VALID)  # 503 no active schedule
    body = resp.json()["error"]
    assert set(body) == {"code", "message", "details", "request_id"}
    assert "Traceback" not in body["message"]
    assert "SELECT" not in body["message"]
