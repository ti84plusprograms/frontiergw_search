"""Public schedule-status response schema (API-003)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ScheduleStatusResponse(BaseModel):
    active: bool
    source: str | None = None
    version: str | None = None
    retrieved_at: datetime | None = None
    effective_start: date | None = None
    effective_end: date | None = None
    route_count: int = 0
    scheduled_flight_count: int = 0
