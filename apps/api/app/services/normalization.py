from datetime import date, time

from app.schemas.schedule_import import NormalizedFlightRecord, RawScheduleRecord


def normalize_flight_record(raw: RawScheduleRecord) -> NormalizedFlightRecord:
    """
    Convert a raw provider record to a normalized internal record.

    Converts provider-specific field formats to standard types:
    - Airport codes: uppercase
    - Times: parse HH:MM → datetime.time
    - Dates: parse YYYY-MM-DD → date
    - Operating days: parse "1,2,3" → [1, 2, 3]

    Args:
        raw: Raw schedule record from provider

    Returns:
        Normalized flight record ready for validation and import

    Raises:
        ValueError: If any field cannot be parsed
    """
    try:
        departure_time = time.fromisoformat(raw.departure_local_time)
        arrival_time = time.fromisoformat(raw.arrival_local_time)
    except ValueError as e:
        raise ValueError(f"Invalid time format: {e}") from e

    try:
        effective_start_date = date.fromisoformat(raw.effective_start)
        effective_end_date = date.fromisoformat(raw.effective_end) if raw.effective_end else None
    except ValueError as e:
        raise ValueError(f"Invalid date format: {e}") from e

    try:
        operating_days_list = (
            [int(d.strip()) for d in raw.operating_days.split(",")]
            if raw.operating_days.strip()
            else []
        )
    except ValueError as e:
        raise ValueError(f"Invalid operating days format: {e}") from e

    if departure_time.tzinfo is not None or arrival_time.tzinfo is not None:
        raise ValueError("Schedule times must be timezone-naive local wall-clock times")

    return NormalizedFlightRecord(
        carrier_code=raw.carrier_code.strip().upper(),
        flight_number=raw.flight_number.strip().upper(),
        origin_code=raw.origin_code.strip().upper(),
        destination_code=raw.destination_code.strip().upper(),
        departure_local_time=departure_time,
        arrival_local_time=arrival_time,
        arrival_day_offset=raw.arrival_day_offset,
        effective_start=effective_start_date,
        effective_end=effective_end_date,
        operating_days=sorted(set(operating_days_list)),
        equipment_code=raw.equipment_code.strip() if raw.equipment_code else None,
    )
