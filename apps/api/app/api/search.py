"""API-002 — itinerary search endpoint.

Validates the public request, maps it to the Phase 3 ``SearchCriteria``, calls the
deterministic routing engine, and serializes the result. A valid search with no
itineraries returns HTTP 200 (PHASE.md §No-Result Behavior).
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.cache_keys import search_key
from app.core.clock import utc_now
from app.core.config import settings
from app.core.metrics import SEARCH_DURATION, SEARCH_NO_RESULTS, SEARCH_REQUESTS, SEARCH_RESULTS
from app.core.observability import log_event
from app.db.session import get_db
from app.domain.errors import InvalidCriteriaError
from app.repositories.schedule import ScheduleRepository
from app.schemas.api_common import ERROR_RESPONSES
from app.schemas.search import SearchCriteria
from app.schemas.search_api import SearchRequest, SearchResponse
from app.services.cache_service import get_cache_service
from app.services.rate_limit import enforce_rate_limit
from app.services.routing.engine import search_itineraries
from app.services.schedule_import import get_active_schedule_status
from app.services.search_response import build_search_response

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse, responses=ERROR_RESPONSES)
def post_search(
    payload: SearchRequest,
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
) -> SearchResponse:
    # Map the public request to the backend-only criteria model. Cross-field rules
    # (e.g. conflicting geography filters) are enforced here and surface as 422.
    try:
        criteria = SearchCriteria(
            origin=payload.origin,
            departure_date=payload.departure_date,
            max_connections=payload.max_connections,
            min_connection_minutes=payload.min_connection_minutes,
            max_connection_minutes=payload.max_connection_minutes,
            depart_after=payload.depart_after,
            depart_before=payload.depart_before,
            arrive_before=payload.arrive_before,
            max_total_duration_minutes=payload.max_total_duration_minutes,
            max_price=payload.max_price,
            domestic_only=payload.domestic_only,
            international_only=payload.international_only,
            sort=payload.sort,
        )
    except ValidationError as exc:
        # Cross-field criteria failures (e.g. domestic_only + international_only) map to
        # a 422 INVALID_REQUEST via the routing-error handler (ADR-009).
        messages = "; ".join(e["msg"] for e in exc.errors())
        raise InvalidCriteriaError(messages or "Invalid search criteria.") from exc

    started = time.perf_counter()
    cache = get_cache_service()
    enforce_rate_limit(
        request,
        endpoint="search",
        limit=settings.search_rate_limit_per_minute,
        cache=cache,
    )
    schedule_status = get_active_schedule_status(db)
    key: str | None = None
    cached_outcome = "BYPASS"
    if schedule_status is not None:
        source = str(schedule_status.get("source") or "unknown")
        version = str(schedule_status.get("version") or "unknown")
        key = search_key(
            settings,
            criteria,
            schedule_source=source,
            schedule_version=version,
            max_results=settings.search_max_results,
        )
        cached = cache.get_json(key, namespace="search")
        cached_outcome = cached.outcome
        if isinstance(cached.value, dict):
            cached_payload = dict(cached.value)
            cached_payload["search_id"] = f"srch_{uuid.uuid4().hex}"
            cached_payload["generated_at"] = utc_now().isoformat()
            try:
                response = SearchResponse.model_validate(cached_payload)
                _record_search(request, criteria, response, started, "HIT", version)
                return response
            except ValidationError:
                cache.delete(key)
                cached_outcome = "CORRUPT"

    lock_token = cache.acquire_lock(key) if key else None
    try:
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

        response = build_search_response(
            origin_airport=origin_airport,
            departure_date=criteria.departure_date,
            itineraries=result.itineraries,
            airports=airports,
            schedule_status=schedule_status,
            max_results=settings.search_max_results,
            generated_at=utc_now(),
        )
        if key:
            cache_payload = response.model_dump(mode="json")
            cache_payload.pop("search_id", None)
            cache_payload.pop("generated_at", None)
            if response.result_count == 0:
                ttl = settings.no_result_cache_ttl_seconds
            elif criteria.departure_date == utc_now().date():
                ttl = settings.same_day_search_cache_ttl_seconds
            else:
                ttl = settings.search_cache_ttl_seconds
            cache.set_json(key, cache_payload, ttl)
        _record_search(
            request,
            criteria,
            response,
            started,
            "MISS" if cached_outcome != "BYPASS" else "BYPASS",
            str(schedule_status.get("version")) if schedule_status else None,
        )
        return response
    finally:
        if key:
            cache.release_lock(key, lock_token)


def _record_search(
    request: Request,
    criteria: SearchCriteria,
    response: SearchResponse,
    started: float,
    cache_status: str,
    schedule_version: str | None,
) -> None:
    duration = time.perf_counter() - started
    SEARCH_REQUESTS.labels(cache_outcome=cache_status).inc()
    SEARCH_DURATION.labels(connections=str(criteria.max_connections)).observe(duration)
    SEARCH_RESULTS.labels(connections=str(criteria.max_connections)).observe(response.result_count)
    if response.result_count == 0:
        SEARCH_NO_RESULTS.inc()
    log_event(
        "search.completed",
        request_id=getattr(request.state, "request_id", None),
        origin=criteria.origin,
        departure_date=criteria.departure_date.isoformat(),
        max_connections=criteria.max_connections,
        result_count=response.result_count,
        cache_status=cache_status,
        schedule_version=schedule_version,
        duration_ms=round(duration * 1000, 3),
    )
