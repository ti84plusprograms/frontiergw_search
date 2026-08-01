"""API-001 — airport search endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.airport import AirportItem, AirportSearchResponse
from app.schemas.api_common import ERROR_RESPONSES
from app.services.airport_search import search_airports

router = APIRouter(tags=["airports"])


@router.get("/airports", response_model=AirportSearchResponse, responses=ERROR_RESPONSES)
def get_airports(
    db: Session = Depends(get_db),  # noqa: B008
    query: str = Query(..., min_length=1, description="Airport code, city, or name."),
    limit: int = Query(
        default=settings.airport_search_default_limit,
        ge=1,
        le=settings.airport_search_max_limit,
        description="Maximum results (bounded).",
    ),
) -> AirportSearchResponse:
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
    return AirportSearchResponse(items=items, count=len(items))
