"""Map Phase 3 routing results into the public search response (API-002).

Pure mapping layer (ADR-006/007/008): money → decimal string, availability →
NOT_CHECKED/LOW, timezone offsets preserved, warnings synthesized, result cap applied
(sort-before-truncate). The routing engine is not modified.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from app.db.models.airport import Airport
from app.domain.enums import AvailabilityStatus
from app.domain.itinerary import Itinerary
from app.schemas.api_common import ApiWarning, WarningCode
from app.schemas.search_api import (
    AirportRef,
    AvailabilityModel,
    DataFreshness,
    ItineraryModel,
    OriginRef,
    PriceModel,
    SearchResponse,
    SegmentModel,
)


def _airport_ref(code: str, airports: dict[str, Airport]) -> AirportRef:
    airport = airports.get(code)
    return AirportRef(
        code=code.upper(),
        city=airport.city if airport else "",
        country_code=airport.country_code if airport else "",
    )


def _price_model(itinerary: Itinerary) -> PriceModel:
    price = itinerary.price
    # Money as a decimal string, never a float (ADR-006); None stays None.
    amount = str(price.amount) if price.amount is not None else None
    return PriceModel(
        amount=amount,
        currency=price.currency,
        status=price.status,
        segment_count=price.segment_count,
        verified_at=price.verified_at,
        disclaimer=price.disclaimer,
    )


def _segments(itinerary: Itinerary) -> list[SegmentModel]:
    segments = []
    for seg in itinerary.segments:
        f = seg.flight
        segments.append(
            SegmentModel(
                sequence=seg.sequence,
                carrier=f.carrier_code,
                flight_number=f.flight_number,
                origin=f.origin_code,
                destination=f.destination_code,
                departure_at=f.departure_at,
                arrival_at=f.arrival_at,
                duration_minutes=f.duration_minutes,
            )
        )
    return segments


def _itinerary_model(itinerary: Itinerary, airports: dict[str, Airport]) -> ItineraryModel:
    return ItineraryModel(
        itinerary_id=itinerary.itinerary_id,
        origin=_airport_ref(itinerary.origin_code, airports),
        destination=_airport_ref(itinerary.destination_code, airports),
        departure_at=itinerary.departure_at,
        arrival_at=itinerary.arrival_at,
        connection_count=itinerary.connection_count,
        total_duration_minutes=itinerary.total_duration_minutes,
        airborne_duration_minutes=itinerary.airborne_duration_minutes,
        total_layover_minutes=itinerary.total_layover_minutes,
        segments=_segments(itinerary),
        # Phase 4 never checks availability (ADR-007).
        availability=AvailabilityModel(
            status=AvailabilityStatus.NOT_CHECKED,
            checked_at=None,
            source=None,
            confidence="LOW",
        ),
        price=_price_model(itinerary),
        booking_url=None,
    )


def build_search_response(
    *,
    origin_airport: Airport,
    departure_date: date,
    itineraries: list[Itinerary],
    airports: dict[str, Airport],
    schedule_status: dict[str, object] | None,
    max_results: int,
    generated_at: datetime | None = None,
) -> SearchResponse:
    """Assemble the public search response from routing output and freshness metadata."""
    now = generated_at or datetime.now(timezone.utc).astimezone()

    truncated = len(itineraries) > max_results
    capped = itineraries[:max_results]  # engine already sorted; truncate after sort

    warnings = [
        ApiWarning(
            code=WarningCode.AVAILABILITY_NOT_CHECKED,
            message="GoWild availability has not been verified.",
        )
    ]
    if not capped:
        warnings.append(
            ApiWarning(
                code=WarningCode.NO_MATCHING_ITINERARIES,
                message="No scheduled itineraries matched the selected criteria.",
            )
        )
    if truncated:
        warnings.append(
            ApiWarning(
                code=WarningCode.RESULTS_TRUNCATED,
                message=f"Results were truncated to the first {max_results} itineraries.",
            )
        )

    status = schedule_status or {}
    freshness = DataFreshness(
        schedule_source=_as_str(status.get("source")),
        schedule_version=_as_str(status.get("version")),
        schedule_updated_at=_as_datetime(status.get("retrieved_at")),
        schedule_effective_start=_as_date(status.get("effective_start")),
        schedule_effective_end=_as_date(status.get("effective_end")),
        availability_checked_at=None,
    )

    return SearchResponse(
        search_id=f"srch_{uuid.uuid4().hex}",
        origin=OriginRef(
            code=origin_airport.code.upper(),
            city=origin_airport.city,
            timezone=origin_airport.timezone,
        ),
        departure_date=departure_date,
        generated_at=now,
        data_freshness=freshness,
        result_count=len(capped),
        results=[_itinerary_model(it, airports) for it in capped],
        warnings=warnings,
    )


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _as_datetime(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _as_date(value: object) -> date | None:
    # datetime is a subclass of date; guard order matters — accept only pure date.
    return value if isinstance(value, date) and not isinstance(value, datetime) else None
