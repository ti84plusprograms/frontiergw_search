"""API-003 schedule-status endpoint tests."""

from __future__ import annotations

from datetime import datetime, time, timezone

import pytest
from pydantic import ValidationError

from app.schemas.schedule_status import ScheduleStatusResponse
from tests.routing_fixtures import add_flight, make_source, seed_airports


def test_no_active_schedule_returns_inactive_body(client, db_session):
    resp = client.get("/api/v1/schedules/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is False
    assert body["source"] is None
    assert body["route_count"] == 0
    assert resp.headers["X-Request-ID"]


def test_active_schedule_status(client, db_session):
    seed_airports(db_session)
    src = make_source(db_session, version="2026-08-01", is_active=True)
    add_flight(db_session, src, origin="ATL", destination="DEN", dep=time(9, 0), arr=time(10, 30))
    resp = client.get("/api/v1/schedules/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] is True
    assert body["source"] == "synthetic-test-schedule"
    assert body["version"] == "2026-08-01"
    assert body["scheduled_flight_count"] == 1
    # Effective range serialized as ISO dates.
    assert body["effective_start"] == "2026-08-01"
    assert body["retrieved_at"].endswith(("Z", "+00:00"))


def test_schedule_status_rejects_naive_timestamp():
    with pytest.raises(ValidationError):
        ScheduleStatusResponse(active=True, retrieved_at=datetime(2026, 8, 1, 12, 0))


def test_schedule_status_accepts_aware_timestamp():
    value = ScheduleStatusResponse(
        active=True, retrieved_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    )
    assert value.retrieved_at is not None
    assert value.retrieved_at.utcoffset() == timezone.utc.utcoffset(value.retrieved_at)
