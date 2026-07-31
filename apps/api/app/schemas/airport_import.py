from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AirportRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str
    name: str
    city: str
    state_or_region: str | None = None
    country_code: str
    latitude: float
    longitude: float
    timezone: str


class AirportImportResult(BaseModel):
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    rejected_count: int = 0
    rejected_reasons: list[dict[str, Any]] = Field(default_factory=list)
