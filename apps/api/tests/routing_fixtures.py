"""SYNTHETIC TEST schedule fixtures for Phase 3 routing integration tests.

THIS IS SYNTHETIC TEST DATA. It does not represent current Frontier inventory.
Provides the 20 fixture scenarios required by PHASE.md §Required Test Fixtures and
helpers to persist airports, data sources, and scheduled flights into a test DB.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from app.db.models.airport import Airport
from app.db.models.data_source import DataSource
from app.db.models.scheduled_flight import ScheduledFlight

# Synthetic airports incl. one international (CUN, Mexico) and one non-DST (PHX).
AIRPORTS = [
    ("ATL", "US", "America/New_York"),
    ("DEN", "US", "America/Denver"),
    ("LAS", "US", "America/Los_Angeles"),
    ("MCO", "US", "America/New_York"),
    ("PHX", "US", "America/Phoenix"),
    ("CUN", "MX", "America/Cancun"),
    ("SEA", "US", "America/Los_Angeles"),
]

ALL_DAYS = [1, 2, 3, 4, 5, 6, 7]


def seed_airports(db: Session) -> None:
    existing = {a.code for a in db.query(Airport).all()}
    for code, country, tz in AIRPORTS:
        if code in existing:
            continue
        db.add(
            Airport(
                code=code,
                name=f"{code} SYNTHETIC",
                city=code,
                country_code=country,
                latitude=1.0,
                longitude=1.0,
                timezone=tz,
            )
        )
    db.flush()


def make_source(db: Session, *, version: str, is_active: bool) -> DataSource:
    source = DataSource(
        id=uuid.uuid4(),
        name="synthetic-test-schedule",
        provider_type="static_test",
        version=version,
        retrieved_at=datetime.now(timezone.utc),
        is_active=is_active,
    )
    db.add(source)
    db.flush()
    return source


def add_flight(
    db: Session,
    source: DataSource,
    *,
    origin: str,
    destination: str,
    dep: time,
    arr: time,
    arrival_day_offset: int = 0,
    operating_days: list[int] | None = None,
    effective_start: date = date(2026, 8, 1),
    effective_end: date | None = date(2026, 12, 31),
    flight_number: str = "100",
) -> ScheduledFlight:
    flight = ScheduledFlight(
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
        operating_days=operating_days or ALL_DAYS,
        data_source_id=source.id,
    )
    db.add(flight)
    db.flush()
    return flight
