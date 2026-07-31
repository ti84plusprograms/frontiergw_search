from sqlalchemy.orm import Session

from app.db import Airport
from app.schemas.schedule_import import NormalizedFlightRecord


class ValidationError(Exception):
    """Raised when a schedule record fails validation."""

    pass


def validate_flight_record(record: NormalizedFlightRecord, db: Session) -> None:
    """
    Validate a normalized flight record against TDD §19.2 rules.

    Checks:
    - Origin airport exists
    - Destination airport exists
    - Origin != destination
    - Carrier code not empty
    - Flight number not empty
    - Operating days valid (1-7, non-empty)
    - Arrival day offset 0-2
    - Effective end >= effective start
    - Departure/arrival times valid (checked by time.fromisoformat in normalization)

    Args:
        record: Normalized flight record
        db: SQLAlchemy session

    Raises:
        ValidationError: If any check fails
    """
    origin_airport = db.query(Airport).filter_by(code=record.origin_code).first()
    if not origin_airport:
        raise ValidationError(f"Unknown airport code: {record.origin_code}")

    dest_airport = db.query(Airport).filter_by(code=record.destination_code).first()
    if not dest_airport:
        raise ValidationError(f"Unknown airport code: {record.destination_code}")

    if record.origin_code == record.destination_code:
        raise ValidationError("Origin and destination cannot be identical")

    if not record.carrier_code.strip():
        raise ValidationError("Missing carrier code")

    if not record.flight_number.strip():
        raise ValidationError("Missing flight number")

    if not record.operating_days:
        raise ValidationError("Operating days cannot be empty")

    for day in record.operating_days:
        if not 1 <= day <= 7:
            raise ValidationError(f"Invalid operating day: {day} (must be 1-7)")

    if not 0 <= record.arrival_day_offset <= 2:
        raise ValidationError(f"Arrival day offset {record.arrival_day_offset} out of range (0-2)")

    if record.effective_end and record.effective_end < record.effective_start:
        raise ValidationError(
            f"Effective end {record.effective_end} is before effective start {record.effective_start}"
        )


def check_batch_quality(records: list[NormalizedFlightRecord]) -> None:
    """
    Run batch-level quality checks per TDD §30.3.

    Checks:
    - Non-zero flight count
    - Effective date range is valid (non-null start, if end is null it's still OK)
    - Duplicate rate (same origin/destination/flight_number/date combination)

    Args:
        records: List of validated flight records

    Raises:
        ValidationError: If any batch-level check fails
    """
    if not records:
        raise ValidationError("No records to import")

    effective_dates_present = any(r.effective_start for r in records)
    if not effective_dates_present:
        raise ValidationError("No records have a valid effective start date")

    # Detect obvious duplicates: same (carrier, flight_number, origin, destination, effective_start)
    seen = set()
    duplicate_count = 0
    for r in records:
        key = (
            r.carrier_code,
            r.flight_number,
            r.origin_code,
            r.destination_code,
            r.effective_start,
        )
        if key in seen:
            duplicate_count += 1
        seen.add(key)

    duplicate_rate = duplicate_count / len(records) if records else 0
    if duplicate_rate > 0.05:  # >5% duplicates
        raise ValidationError(f"Duplicate rate too high: {duplicate_rate:.1%}")
