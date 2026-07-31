"""Test database models and constraints."""

import pytest
from sqlalchemy import exc

from app.db import Airport, DataSource, Route, ScheduledFlight


def test_airport_creation(db_session):
    """Test creating an airport."""
    airport = Airport(
        code="ATL",
        name="Hartsfield-Jackson Atlanta International",
        city="Atlanta",
        country_code="US",
        latitude=33.6407,
        longitude=-84.4277,
        timezone="America/New_York",
    )
    db_session.add(airport)
    db_session.commit()

    retrieved = db_session.query(Airport).filter_by(code="ATL").first()
    assert retrieved is not None
    assert retrieved.name == "Hartsfield-Jackson Atlanta International"
    assert retrieved.is_active is True


def test_airport_code_is_primary_key(db_session):
    """Test that airport code is the primary key."""
    airport1 = Airport(
        code="ATL",
        name="ATL Airport",
        city="Atlanta",
        country_code="US",
        latitude=1.0,
        longitude=1.0,
        timezone="America/New_York",
    )
    db_session.add(airport1)
    db_session.commit()

    # Trying to insert a duplicate code should fail
    airport2 = Airport(
        code="ATL",
        name="Different name",
        city="Different city",
        country_code="US",
        latitude=2.0,
        longitude=2.0,
        timezone="America/New_York",
    )
    db_session.add(airport2)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()


def test_route_no_self_loop(db_session):
    """Test that route origin != destination CHECK constraint."""
    airport = Airport(
        code="ATL",
        name="ATL",
        city="Atlanta",
        country_code="US",
        latitude=1.0,
        longitude=1.0,
        timezone="America/New_York",
    )
    source = DataSource(
        name="test",
        provider_type="test",
        version="v1",
    )
    db_session.add_all([airport, source])
    db_session.flush()

    route = Route(
        origin_code="ATL",
        destination_code="ATL",
        effective_start=__import__("datetime").date(2026, 8, 1),
        operating_days=[1, 2, 3],
        data_source_id=source.id,
    )
    db_session.add(route)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()


def test_scheduled_flight_no_self_loop(db_session):
    """Test that scheduled flight origin != destination CHECK constraint."""
    airport = Airport(
        code="ATL",
        name="ATL",
        city="Atlanta",
        country_code="US",
        latitude=1.0,
        longitude=1.0,
        timezone="America/New_York",
    )
    source = DataSource(
        name="test",
        provider_type="test",
        version="v1",
    )
    db_session.add_all([airport, source])
    db_session.flush()

    import datetime

    flight = ScheduledFlight(
        carrier_code="F9",
        flight_number="100",
        origin_code="ATL",
        destination_code="ATL",
        departure_local_time=datetime.time(6, 0),
        arrival_local_time=datetime.time(6, 30),
        arrival_day_offset=0,
        effective_start=datetime.date(2026, 8, 1),
        operating_days=[1, 2, 3],
        data_source_id=source.id,
    )
    db_session.add(flight)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()


def test_scheduled_flight_arrival_day_offset_check(db_session):
    """Test that arrival_day_offset is 0-2."""
    airport_atl = Airport(
        code="ATL",
        name="ATL",
        city="Atlanta",
        country_code="US",
        latitude=1.0,
        longitude=1.0,
        timezone="America/New_York",
    )
    airport_den = Airport(
        code="DEN",
        name="DEN",
        city="Denver",
        country_code="US",
        latitude=2.0,
        longitude=2.0,
        timezone="America/Denver",
    )
    source = DataSource(
        name="test",
        provider_type="test",
        version="v1",
    )
    db_session.add_all([airport_atl, airport_den, source])
    db_session.flush()

    import datetime

    # Valid offset 0
    flight_valid = ScheduledFlight(
        carrier_code="F9",
        flight_number="100",
        origin_code="ATL",
        destination_code="DEN",
        departure_local_time=datetime.time(6, 0),
        arrival_local_time=datetime.time(8, 30),
        arrival_day_offset=0,
        effective_start=datetime.date(2026, 8, 1),
        operating_days=[1, 2, 3],
        data_source_id=source.id,
    )
    db_session.add(flight_valid)
    db_session.commit()

    # Invalid offset 3
    flight_invalid = ScheduledFlight(
        carrier_code="F9",
        flight_number="101",
        origin_code="ATL",
        destination_code="DEN",
        departure_local_time=datetime.time(6, 0),
        arrival_local_time=datetime.time(8, 30),
        arrival_day_offset=3,
        effective_start=datetime.date(2026, 8, 1),
        operating_days=[1, 2, 3],
        data_source_id=source.id,
    )
    db_session.add(flight_invalid)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()


def test_flight_foreign_key_constraint(db_session):
    """Test that flight origin/destination must reference valid airports."""
    import datetime

    source = DataSource(
        name="test",
        provider_type="test",
        version="v1",
    )
    db_session.add(source)
    db_session.flush()

    # Try to insert a flight with non-existent origin airport
    flight = ScheduledFlight(
        carrier_code="F9",
        flight_number="100",
        origin_code="XXX",  # Doesn't exist
        destination_code="YYY",  # Doesn't exist
        departure_local_time=datetime.time(6, 0),
        arrival_local_time=datetime.time(8, 30),
        arrival_day_offset=0,
        effective_start=datetime.date(2026, 8, 1),
        operating_days=[1, 2, 3],
        data_source_id=source.id,
    )
    db_session.add(flight)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
