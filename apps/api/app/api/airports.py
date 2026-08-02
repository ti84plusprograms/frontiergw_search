"""API-001 — airport search endpoint."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Query, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.cache_keys import airport_search_key
from app.core.config import settings
from app.core.metrics import AIRPORT_DURATION, AIRPORT_REQUESTS
from app.core.observability import log_event
from app.db.session import get_db
from app.schemas.airport import AirportItem, AirportSearchResponse
from app.schemas.api_common import ERROR_RESPONSES
from app.services.airport_search import search_airports
from app.services.cache_service import get_cache_service
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(tags=["airports"])


@router.get("/airports", response_model=AirportSearchResponse, responses=ERROR_RESPONSES)
def get_airports(
    request: Request,
    db: Session = Depends(get_db),  # noqa: B008
    query: str = Query(
        ...,
        min_length=1,
        pattern=r".*\S.*",
        max_length=settings.airport_query_max_length,
        description="Non-whitespace airport code, city, or name.",
    ),
    limit: int = Query(
        default=settings.airport_search_default_limit,
        ge=1,
        le=settings.airport_search_max_limit,
        description="Maximum results (bounded).",
    ),
) -> AirportSearchResponse:
    started = time.perf_counter()
    cache = get_cache_service()
    enforce_rate_limit(
        request,
        endpoint="airports",
        limit=settings.airport_rate_limit_per_minute,
        cache=cache,
    )
    key = airport_search_key(settings, query, limit)
    cached = cache.get_json(key, namespace="airports")
    if isinstance(cached.value, dict):
        try:
            response = AirportSearchResponse.model_validate(cached.value)
            _record_airport(
                request, started, len(response.items), cached.outcome, len(query.strip())
            )
            return response
        except ValidationError:
            cache.delete(key)

    airports = search_airports(db, query=query, limit=limit)
    items = [
        AirportItem(
            code=a.code.upper(),
            name=a.name,
            city=a.city,
            state_or_region=a.state_or_region,
            country_code=a.country_code,
            timezone=a.timezone,
        )
        for a in airports
    ]
    response = AirportSearchResponse(items=items, count=len(items))
    cache.set_json(
        key,
        response.model_dump(mode="json"),
        settings.airport_search_cache_ttl_seconds,
    )
    _record_airport(request, started, len(items), cached.outcome, len(query.strip()))
    return response


def _record_airport(
    request: Request, started: float, result_count: int, cache_status: str, query_length: int
) -> None:
    duration = time.perf_counter() - started
    AIRPORT_REQUESTS.inc()
    AIRPORT_DURATION.observe(duration)
    log_event(
        "airport_search.completed",
        request_id=getattr(request.state, "request_id", None),
        query_length=query_length,
        result_count=result_count,
        cache_status=cache_status,
        duration_ms=round(duration * 1000, 3),
    )
