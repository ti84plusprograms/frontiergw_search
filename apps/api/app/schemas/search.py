"""Validated search-criteria model for the routing engine (RTE-006 input).

Backend-only domain/Pydantic model — NOT a public HTTP schema (PHASE.md §1). Validation
rules follow PHASE.md §1 and TDD §19.1. Invalid criteria fail before schedule traversal.
"""

from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import SortMode


class SearchCriteria(BaseModel):
    model_config = ConfigDict(frozen=True)

    origin: str
    departure_date: date
    max_connections: int = Field(default=1, ge=0, le=1)
    min_connection_minutes: int = Field(default=45, ge=20, le=360)
    max_connection_minutes: int = Field(default=240, ge=20, le=360)
    depart_after: time | None = None
    depart_before: time | None = None
    arrive_before: time | None = None
    max_total_duration_minutes: int | None = Field(default=720, ge=60, le=1440)
    max_price: float | None = None
    domestic_only: bool = False
    international_only: bool = False
    sort: SortMode = SortMode.PRICE

    @field_validator("origin")
    @classmethod
    def _normalize_origin(cls, value: str) -> str:
        code = value.strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValueError("origin must be exactly three alphabetical characters")
        return code

    @field_validator("max_price")
    @classmethod
    def _nonnegative_price(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("max_price must be nonnegative")
        return value

    @model_validator(mode="after")
    def _cross_field(self) -> SearchCriteria:
        if self.max_connection_minutes < self.min_connection_minutes:
            raise ValueError("max_connection_minutes must be >= min_connection_minutes")
        if self.domestic_only and self.international_only:
            raise ValueError("domestic_only and international_only cannot both be true")
        return self
