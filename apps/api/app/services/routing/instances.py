"""Resolve scheduled-flight definitions into dated, timezone-aware flight instances.

RTE-001. Implements PHASE.md §Flight-Instance Resolution, §Effective-Date Handling,
§Weekday Handling, and the DST ambiguous/nonexistent-time rejection rule (ADR-003).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.db.models.airport import Airport
from app.db.models.scheduled_flight import ScheduledFlight
from app.domain.flight_instance import FlightInstance


@dataclass(frozen=True, slots=True)
class ResolutionSkip:
    """Diagnostic for a schedule definition that did not resolve on the given date."""

    scheduled_flight_id: object
    reason: str


def operates_on(flight: ScheduledFlight, operating_date: date) -> bool:
    """Whether a scheduled flight is applicable on ``operating_date``.

    Effective-date bounds are inclusive; weekday uses ISO values 1=Mon..7=Sun taken
    from the requested date, not from any UTC conversion (PHASE.md §3, §4).
    """
    if operating_date < flight.effective_start:
        return False
    if flight.effective_end is not None and operating_date > flight.effective_end:
        return False
    return operating_date.isoweekday() in flight.operating_days


def _localize(local_dt: datetime, tz: ZoneInfo) -> datetime | None:
    """Attach ``tz`` to a naive local datetime, rejecting DST gap/fold times.

    Returns None when the wall-clock time is nonexistent (spring-forward gap) or
    ambiguous (fall-back fold), per ADR-003. Otherwise returns the aware datetime.
    """
    aware = local_dt.replace(tzinfo=tz)
    # Nonexistent (gap): normalizing through UTC and back changes the wall clock.
    roundtrip = aware.astimezone(ZoneInfo("UTC")).astimezone(tz)
    if roundtrip.replace(tzinfo=None) != local_dt:
        return None
    # Ambiguous (fold): the two fold interpretations map to different instants.
    if aware.utcoffset() != aware.replace(fold=1).utcoffset():
        return None
    return aware


def resolve_instance(
    flight: ScheduledFlight,
    operating_date: date,
    origin: Airport,
    destination: Airport,
) -> FlightInstance | ResolutionSkip:
    """Resolve one scheduled flight for one date into a timezone-aware instance.

    Returns a :class:`ResolutionSkip` (not an exception) when the flight does not
    operate on the date or cannot be resolved deterministically; these are expected,
    not error conditions.
    """
    if not operates_on(flight, operating_date):
        return ResolutionSkip(flight.id, "not_operating_on_date")

    try:
        origin_tz = ZoneInfo(origin.timezone)
        dest_tz = ZoneInfo(destination.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ResolutionSkip(flight.id, "invalid_timezone")

    dep_local = datetime.combine(operating_date, _as_time(flight.departure_local_time))
    arr_date = operating_date + timedelta(days=flight.arrival_day_offset)
    arr_local = datetime.combine(arr_date, _as_time(flight.arrival_local_time))

    departure_at = _localize(dep_local, origin_tz)
    arrival_at = _localize(arr_local, dest_tz)
    if departure_at is None:
        return ResolutionSkip(flight.id, "nonexistent_or_ambiguous_departure")
    if arrival_at is None:
        return ResolutionSkip(flight.id, "nonexistent_or_ambiguous_arrival")

    if arrival_at <= departure_at:
        return ResolutionSkip(flight.id, "nonpositive_duration")

    return FlightInstance(
        scheduled_flight_id=flight.id,
        carrier_code=flight.carrier_code,
        flight_number=flight.flight_number,
        origin_code=flight.origin_code,
        destination_code=flight.destination_code,
        departure_at=departure_at,
        arrival_at=arrival_at,
        operating_date=operating_date,
        data_source_id=flight.data_source_id,
    )


def _as_time(value: time) -> time:
    # Schedule times are stored tz-naive; guard against accidental tz-aware values.
    if value.tzinfo is not None:
        raise ValueError("scheduled local time must be tz-naive wall-clock")
    return value
