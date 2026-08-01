"""Deterministic itinerary filtering (RTE-006).

PHASE.md §13. Time filters apply to the itinerary's initial departure / final arrival
in the relevant airport's LOCAL time (the aware datetime already carries that offset).
Duration filters use elapsed minutes; price filter uses the estimated total; geographic
filters compare origin vs destination country codes.
"""

from __future__ import annotations

from decimal import Decimal

from app.db.models.airport import Airport
from app.domain.itinerary import Itinerary
from app.schemas.search import SearchCriteria


def _country(airports: dict[str, Airport], code: str) -> str | None:
    airport = airports.get(code)
    return airport.country_code if airport else None


def matches(itinerary: Itinerary, criteria: SearchCriteria, airports: dict[str, Airport]) -> bool:
    if itinerary.connection_count > criteria.max_connections:
        return False

    dep_local = itinerary.departure_at.timetz().replace(tzinfo=None)
    arr_local = itinerary.arrival_at.timetz().replace(tzinfo=None)

    if criteria.depart_after is not None and dep_local < criteria.depart_after:
        return False
    if criteria.depart_before is not None and dep_local > criteria.depart_before:
        return False
    if criteria.arrive_before is not None and arr_local > criteria.arrive_before:
        return False

    if (
        criteria.max_total_duration_minutes is not None
        and itinerary.total_duration_minutes > criteria.max_total_duration_minutes
    ):
        return False

    if criteria.max_price is not None:
        amount = itinerary.price.amount
        # Unknown/None estimates are not excluded by a price ceiling.
        if amount is not None and amount > Decimal(str(criteria.max_price)):
            return False

    origin_country = _country(airports, itinerary.origin_code)
    dest_country = _country(airports, itinerary.destination_code)
    if criteria.domestic_only:
        if origin_country is None or dest_country is None or origin_country != dest_country:
            return False
    if criteria.international_only:
        if origin_country is None or dest_country is None or origin_country == dest_country:
            return False

    return True


def apply_filters(
    itineraries: list[Itinerary],
    criteria: SearchCriteria,
    airports: dict[str, Airport],
) -> list[Itinerary]:
    return [it for it in itineraries if matches(it, criteria, airports)]
