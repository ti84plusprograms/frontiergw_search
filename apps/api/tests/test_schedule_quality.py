"""Test schedule data quality checks."""

from datetime import date, time

import pytest

from app.db import Airport
from app.schemas.schedule_import import NormalizedFlightRecord
from app.services.schedule_quality import ValidationError, validate_flight_record


def test_validate_flight_unknown_origin(db_session):
    """Validation fails for unknown origin airport."""
    den = Airport(
        code="DEN",
        name="Denver",
        city="Denver",
        country_code="US",
        latitude=39.8,
        longitude=-104.6,
        timezone="America/Denver",
    )
    db_session.add(den)
    db_session.flush()

    record = NormalizedFlightRecord(
        carrier_code="F9",
        flight_number="100",
        origin_code="XXX",
        destination_code="DEN",
        departure_local_time=time(6, 0),
        arrival_local_time=time(8, 30),
        arrival_day_offset=0,
        effective_start=date(2026, 8, 1),
        effective_end=None,
        operating_days=[1, 2, 3],
    )

    with pytest.raises(ValidationError, match="Unknown airport code"):
        validate_flight_record(record, db_session)


def test_validate_flight_self_loop(db_session):
    """Validation fails for self-loop."""
    atl = Airport(
        code="ATL",
        name="Atlanta",
        city="Atlanta",
        country_code="US",
        latitude=33.6,
        longitude=-84.4,
        timezone="America/New_York",
    )
    db_session.add(atl)
    db_session.flush()

    record = NormalizedFlightRecord(
        carrier_code="F9",
        flight_number="100",
        origin_code="ATL",
        destination_code="ATL",
        departure_local_time=time(6, 0),
        arrival_local_time=time(8, 30),
        arrival_day_offset=0,
        effective_start=date(2026, 8, 1),
        effective_end=None,
        operating_days=[1, 2, 3],
    )

    with pytest.raises(ValidationError, match="cannot be identical"):
        validate_flight_record(record, db_session)


def test_validate_flight_missing_number(db_session):
    """Validation fails for empty flight number."""
    atl = Airport(
        code="ATL",
        name="Atlanta",
        city="Atlanta",
        country_code="US",
        latitude=33.6,
        longitude=-84.4,
        timezone="America/New_York",
    )
    den = Airport(
        code="DEN",
        name="Denver",
        city="Denver",
        country_code="US",
        latitude=39.8,
        longitude=-104.6,
        timezone="America/Denver",
    )
    db_session.add_all([atl, den])
    db_session.flush()

    record = NormalizedFlightRecord(
        carrier_code="F9",
        flight_number="",
        origin_code="ATL",
        destination_code="DEN",
        departure_local_time=time(6, 0),
        arrival_local_time=time(8, 30),
        arrival_day_offset=0,
        effective_start=date(2026, 8, 1),
        effective_end=None,
        operating_days=[1, 2, 3],
    )

    with pytest.raises(ValidationError, match="Missing flight number"):
        validate_flight_record(record, db_session)


def test_validate_flight_bad_day_offset(db_session):
    """Validation fails for arrival_day_offset outside 0-2."""
    atl = Airport(
        code="ATL",
        name="Atlanta",
        city="Atlanta",
        country_code="US",
        latitude=33.6,
        longitude=-84.4,
        timezone="America/New_York",
    )
    den = Airport(
        code="DEN",
        name="Denver",
        city="Denver",
        country_code="US",
        latitude=39.8,
        longitude=-104.6,
        timezone="America/Denver",
    )
    db_session.add_all([atl, den])
    db_session.flush()

    record = NormalizedFlightRecord(
        carrier_code="F9",
        flight_number="100",
        origin_code="ATL",
        destination_code="DEN",
        departure_local_time=time(6, 0),
        arrival_local_time=time(8, 30),
        arrival_day_offset=5,
        effective_start=date(2026, 8, 1),
        effective_end=None,
        operating_days=[1, 2, 3],
    )

    with pytest.raises(ValidationError, match="out of range"):
        validate_flight_record(record, db_session)


def test_validate_flight_bad_operating_days(db_session):
    """Validation fails for invalid operating day values."""
    atl = Airport(
        code="ATL",
        name="Atlanta",
        city="Atlanta",
        country_code="US",
        latitude=33.6,
        longitude=-84.4,
        timezone="America/New_York",
    )
    den = Airport(
        code="DEN",
        name="Denver",
        city="Denver",
        country_code="US",
        latitude=39.8,
        longitude=-104.6,
        timezone="America/Denver",
    )
    db_session.add_all([atl, den])
    db_session.flush()

    record = NormalizedFlightRecord(
        carrier_code="F9",
        flight_number="100",
        origin_code="ATL",
        destination_code="DEN",
        departure_local_time=time(6, 0),
        arrival_local_time=time(8, 30),
        arrival_day_offset=0,
        effective_start=date(2026, 8, 1),
        effective_end=None,
        operating_days=[1, 9],
    )

    with pytest.raises(ValidationError, match="Invalid operating day"):
        validate_flight_record(record, db_session)


def test_validate_flight_empty_operating_days(db_session):
    """Validation fails for empty operating days."""
    atl = Airport(
        code="ATL",
        name="Atlanta",
        city="Atlanta",
        country_code="US",
        latitude=33.6,
        longitude=-84.4,
        timezone="America/New_York",
    )
    den = Airport(
        code="DEN",
        name="Denver",
        city="Denver",
        country_code="US",
        latitude=39.8,
        longitude=-104.6,
        timezone="America/Denver",
    )
    db_session.add_all([atl, den])
    db_session.flush()

    record = NormalizedFlightRecord(
        carrier_code="F9",
        flight_number="100",
        origin_code="ATL",
        destination_code="DEN",
        departure_local_time=time(6, 0),
        arrival_local_time=time(8, 30),
        arrival_day_offset=0,
        effective_start=date(2026, 8, 1),
        effective_end=None,
        operating_days=[],
    )

    with pytest.raises(ValidationError, match="cannot be empty"):
        validate_flight_record(record, db_session)


def test_validate_flight_effective_range(db_session):
    """Validation fails when effective_end < effective_start."""
    atl = Airport(
        code="ATL",
        name="Atlanta",
        city="Atlanta",
        country_code="US",
        latitude=33.6,
        longitude=-84.4,
        timezone="America/New_York",
    )
    den = Airport(
        code="DEN",
        name="Denver",
        city="Denver",
        country_code="US",
        latitude=39.8,
        longitude=-104.6,
        timezone="America/Denver",
    )
    db_session.add_all([atl, den])
    db_session.flush()

    record = NormalizedFlightRecord(
        carrier_code="F9",
        flight_number="100",
        origin_code="ATL",
        destination_code="DEN",
        departure_local_time=time(6, 0),
        arrival_local_time=time(8, 30),
        arrival_day_offset=0,
        effective_start=date(2026, 12, 31),
        effective_end=date(2026, 8, 1),
        operating_days=[1, 2, 3],
    )

    with pytest.raises(ValidationError, match="before effective start"):
        validate_flight_record(record, db_session)
