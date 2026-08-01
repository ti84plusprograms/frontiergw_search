"""Routing engine orchestrator: search_itineraries (RTE-002..007 wired together).

Follows the PHASE.md Direct/One-Stop Search Flow and reference pseudocode. Pure and
deterministic: same dataset + config + criteria -> same results in the same order.
Read-only with respect to schedule data (PHASE.md §Read-Only Routing).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.config import settings as default_settings
from app.domain.errors import (
    DateOutsideScheduleRangeError,
    InvalidTimezoneError,
    NoActiveScheduleError,
    UnknownOriginError,
)
from app.domain.itinerary import Itinerary
from app.repositories.schedule import ScheduleRepository
from app.schemas.search import SearchCriteria
from app.services.routing.connections import ConnectionPolicy
from app.services.routing.dedup import deduplicate
from app.services.routing.filters import apply_filters
from app.services.routing.pricing import PriceEstimator
from app.services.routing.search import SearchDiagnostics, generate_itineraries
from app.services.routing.sorting import sort_itineraries
from app.services.schedule_import import get_active_schedule_status


@dataclass(frozen=True, slots=True)
class SearchResult:
    itineraries: list[Itinerary]
    active_source_name: str
    active_source_version: str
    diagnostics: dict[str, int] = field(default_factory=dict)


def _policy(criteria: SearchCriteria) -> ConnectionPolicy:
    return ConnectionPolicy(
        min_connection_minutes=criteria.min_connection_minutes,
        max_connection_minutes=criteria.max_connection_minutes,
        max_total_duration_minutes=(criteria.max_total_duration_minutes or 24 * 60),
    )


def _within_coverage(status: dict[str, object], departure_date: date) -> bool:
    start = status.get("effective_start")
    end = status.get("effective_end")
    if isinstance(start, date) and departure_date < start:
        return False
    if isinstance(end, date) and departure_date > end:
        return False
    return True


def search_itineraries(
    db: Session,
    criteria: SearchCriteria,
    *,
    config: Settings | None = None,
) -> SearchResult:
    """Deterministically search direct + one-stop itineraries for the criteria.

    Raises typed :mod:`app.domain.errors` for invalid-origin / no-active-schedule /
    date-outside-coverage. An empty itinerary list is a valid no-result outcome, NOT
    an error (PHASE.md §Error and Diagnostic Requirements).
    """
    cfg = config or default_settings
    repo = ScheduleRepository(db)

    status = get_active_schedule_status(db)
    if status is None or repo.active_source_id() is None:
        raise NoActiveScheduleError("no active schedule dataset")

    if not _within_coverage(status, criteria.departure_date):
        raise DateOutsideScheduleRangeError(
            f"departure_date {criteria.departure_date} is outside active schedule coverage"
        )

    origin_airport = repo.airports_by_code([criteria.origin]).get(criteria.origin)
    if origin_airport is None or not origin_airport.is_active:
        raise UnknownOriginError(f"unknown or inactive origin airport: {criteria.origin}")

    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(origin_airport.timezone)
    except Exception as exc:  # noqa: BLE001 - normalize to typed domain error
        raise InvalidTimezoneError(
            f"origin airport {criteria.origin} has invalid timezone metadata"
        ) from exc

    # Bulk-load every airport the search may reference (origin, first-leg destinations,
    # and second-leg destinations) in a bounded number of queries — no per-row N+1.
    first_flights = repo.find_departures(criteria.origin, criteria.departure_date)
    codes: set[str] = {criteria.origin}
    mid_codes: set[str] = set()
    for f in first_flights:
        codes.add(f.destination_code)
        mid_codes.add(f.destination_code)
    if criteria.max_connections >= 1 and cfg.max_supported_connections >= 1:
        for mid in sorted(mid_codes):
            for second, _d in repo.find_departures_for_dates(
                mid, [criteria.departure_date, criteria.departure_date]
            ):
                codes.add(second.destination_code)
    airports = repo.airports_by_code(codes)

    estimator = PriceEstimator(
        domestic_segment_price=Decimal(cfg.domestic_estimated_segment_price_usd),
        international_estimation_enabled=cfg.international_estimation_enabled,
    )
    diagnostics = SearchDiagnostics()

    raw = generate_itineraries(
        repo,
        criteria.origin,
        criteria.departure_date,
        max_connections=min(criteria.max_connections, cfg.max_supported_connections),
        policy=_policy(criteria),
        estimator=estimator,
        airports=airports,
        diagnostics=diagnostics,
    )

    filtered = apply_filters(raw, criteria, airports)
    deduped = deduplicate(filtered)
    ordered = sort_itineraries(deduped, criteria.sort)

    return SearchResult(
        itineraries=ordered,
        active_source_name=str(status["source"]),
        active_source_version=str(status["version"]),
        diagnostics={
            "first_segment_candidates": diagnostics.first_segment_candidates,
            "second_segment_candidates": diagnostics.second_segment_candidates,
            "rejected_connections": diagnostics.rejected_connections,
            "deduplicated": len(filtered) - len(deduped),
            "result_count": len(ordered),
        },
    )
