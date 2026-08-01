"""API-002 — itinerary search endpoint.

Validates the public request, maps it to the Phase 3 ``SearchCriteria``, calls the
deterministic routing engine, and serializes the result. A valid search with no
itineraries returns HTTP 200 (PHASE.md §No-Result Behavior).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.domain.errors import InvalidCriteriaError
from app.repositories.schedule import ScheduleRepository
from app.schemas.api_common import ERROR_RESPONSES
from app.schemas.search import SearchCriteria
from app.schemas.search_api import SearchRequest, SearchResponse
from app.services.routing.engine import search_itineraries
from app.services.schedule_import import get_active_schedule_status
from app.services.search_response import build_search_response

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse, responses=ERROR_RESPONSES)
def post_search(
    request: SearchRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> SearchResponse:
    # Map the public request to the backend-only criteria model. Cross-field rules
    # (e.g. conflicting geography filters) are enforced here and surface as 422.
    try:
        criteria = SearchCriteria(
            origin=request.origin,
            departure_date=request.departure_date,
            max_connections=request.max_connections,
            min_connection_minutes=request.min_connection_minutes,
            max_connection_minutes=request.max_connection_minutes,
            depart_after=request.depart_after,
            depart_before=request.depart_before,
            arrive_before=request.arrive_before,
            max_total_duration_minutes=request.max_total_duration_minutes,
            max_price=request.max_price,
            domestic_only=request.domestic_only,
            international_only=request.international_only,
            sort=request.sort,
        )
    except ValidationError as exc:
        # Cross-field criteria failures (e.g. domestic_only + international_only) map to
        # a 422 INVALID_REQUEST via the routing-error handler (ADR-009).
        messages = "; ".join(e["msg"] for e in exc.errors())
        raise InvalidCriteriaError(messages or "Invalid search criteria.") from exc

    result = search_itineraries(db, criteria)

    # Bulk-load airport metadata for every code appearing in the results (no N+1).
    repo = ScheduleRepository(db)
    codes: set[str] = {criteria.origin}
    for itinerary in result.itineraries:
        codes.add(itinerary.origin_code)
        codes.add(itinerary.destination_code)
        for seg in itinerary.segments:
            codes.add(seg.flight.origin_code)
            codes.add(seg.flight.destination_code)
    airports = repo.airports_by_code(codes)
    origin_airport = airports[criteria.origin]

    return build_search_response(
        origin_airport=origin_airport,
        departure_date=criteria.departure_date,
        itineraries=result.itineraries,
        airports=airports,
        schedule_status=get_active_schedule_status(db),
        max_results=settings.search_max_results,
    )
