"""Public search request/response schemas (API-002).

The request is strict (``extra="forbid"``) so unknown fields are rejected (422). These
are the public HTTP contract; they map to/from the backend-only ``SearchCriteria`` and
the Phase 3 ``Itinerary`` domain objects. Money is a decimal string (ADR-006); datetimes
are ISO-8601 with offsets (timezone preserved).
"""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AvailabilityStatus, PriceStatus, SortMode
from app.schemas.api_common import ApiWarning


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: str
    departure_date: date
    max_connections: int = Field(default=1, ge=0, le=1)
    min_connection_minutes: int = Field(default=45, gt=0)
    max_connection_minutes: int = Field(default=240, gt=0)
    depart_after: time | None = None
    depart_before: time | None = None
    arrive_before: time | None = None
    max_total_duration_minutes: int | None = Field(default=720)
    max_price: float | None = None
    domestic_only: bool = False
    international_only: bool = False
    sort: SortMode = SortMode.PRICE


class AirportRef(BaseModel):
    code: str
    city: str
    country_code: str


class OriginRef(BaseModel):
    code: str
    city: str
    timezone: str


class SegmentModel(BaseModel):
    sequence: int
    carrier: str
    flight_number: str
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int


class PriceModel(BaseModel):
    amount: str | None
    currency: str
    status: PriceStatus
    segment_count: int
    verified_at: datetime | None = None
    disclaimer: str


class AvailabilityModel(BaseModel):
    status: AvailabilityStatus
    checked_at: datetime | None = None
    source: str | None = None
    confidence: str = "LOW"


class ItineraryModel(BaseModel):
    itinerary_id: str
    origin: AirportRef
    destination: AirportRef
    departure_at: datetime
    arrival_at: datetime
    connection_count: int
    total_duration_minutes: int
    airborne_duration_minutes: int
    total_layover_minutes: int
    segments: list[SegmentModel]
    price: PriceModel
    availability: AvailabilityModel
    booking_url: str | None = None


class DataFreshness(BaseModel):
    schedule_source: str | None
    schedule_version: str | None
    schedule_updated_at: datetime | None
    schedule_effective_start: date | None
    schedule_effective_end: date | None
    availability_checked_at: datetime | None = None


class SearchResponse(BaseModel):
    search_id: str
    origin: OriginRef
    departure_date: date
    generated_at: datetime
    data_freshness: DataFreshness
    result_count: int
    results: list[ItineraryModel]
    warnings: list[ApiWarning]
