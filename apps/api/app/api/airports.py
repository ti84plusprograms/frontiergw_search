from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Airport
from app.db.session import get_db

router = APIRouter()


class AirportResult(BaseModel):
    code: str
    name: str
    city: str
    state_or_region: str | None
    country_code: str
    timezone: str
    latitude: float
    longitude: float


class AirportSearchResponse(BaseModel):
    items: list[AirportResult]


@router.get("/airports", response_model=AirportSearchResponse)
def search_airports(
    query: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),  # noqa: B008
) -> AirportSearchResponse:
    normalized_query = query.strip().upper()
    if not normalized_query:
        return AirportSearchResponse(items=[])

    search_pattern = f"%{normalized_query}%"
    statement = (
        select(Airport)
        .where(
            Airport.is_active.is_(True),
            or_(
                Airport.code.ilike(search_pattern),
                Airport.city.ilike(search_pattern),
                Airport.name.ilike(search_pattern),
            ),
        )
        .order_by(Airport.code)
        .limit(limit)
    )
    airports = db.scalars(statement).all()
    return AirportSearchResponse(
        items=[
            AirportResult(
                code=airport.code,
                name=airport.name,
                city=airport.city,
                state_or_region=airport.state_or_region,
                country_code=airport.country_code,
                timezone=airport.timezone,
                latitude=airport.latitude,
                longitude=airport.longitude,
            )
            for airport in airports
        ]
    )
