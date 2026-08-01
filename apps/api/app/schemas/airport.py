"""Public airport response schemas (API-001).

Only the documented public fields are exposed (PHASE.md API-001 response model);
internal DB identifiers/coordinates are not serialized.
"""

from __future__ import annotations

from pydantic import BaseModel


class AirportItem(BaseModel):
    code: str
    name: str
    city: str
    state_or_region: str | None
    country_code: str
    timezone: str


class AirportSearchResponse(BaseModel):
    items: list[AirportItem]
    count: int
